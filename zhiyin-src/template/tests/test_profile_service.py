"""画像服务的业务行为测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from zhiyin_business.events import PROFILE_FIELD_UPDATED, ProfileFieldUpdatedPayload
from zhiyin_business.services.profile import DefaultProfileService
from zhiyin_infrastructure.local.repository import (
    InMemoryProfileRepository,
    LocalJsonRegistryRepository,
)
from zhiyin_kernel.blackboard import ProfileGap
from zhiyin_orchestration import DomainEvent, EventBus

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]


class RecordingEventBus(EventBus):
    def __init__(self, *, error: Exception | None = None) -> None:
        self.events: list[DomainEvent] = []
        self.error = error

    async def publish(self, event: DomainEvent) -> None:
        if self.error is not None:
            raise self.error
        self.events.append(event)

    def subscribe(self, event_type: str, handler) -> None:
        pass

    def unsubscribe(self, event_type: str, handler) -> None:
        pass


@pytest.fixture
def repository() -> InMemoryProfileRepository:
    return InMemoryProfileRepository()


@pytest.fixture
def registry() -> LocalJsonRegistryRepository:
    return LocalJsonRegistryRepository(str(TEMPLATE_ROOT / "data" / "registry"))


@pytest.fixture
def bus() -> RecordingEventBus:
    return RecordingEventBus()


@pytest.fixture
def service(repository, registry, bus) -> DefaultProfileService:
    return DefaultProfileService(repository, registry, bus)


async def test_empty_profile_reads(service: DefaultProfileService) -> None:
    assert await service.get("u1") is None
    assert await service.get_fields("u1") == []
    assert await service.get_gaps("u1") == []
    assert await service.overall_confidence("u1") == 0.0


async def test_update_and_overwrite_field(
    service: DefaultProfileService, bus: RecordingEventBus
) -> None:
    first = await service.update_field(
        "u1",
        "career_interest",
        "engineering",
        confidence=0.6,
        source="conversation",
        evidence=["turn-1"],
    )
    second = await service.update_field(
        "u1",
        "career_interest",
        "design",
        confidence=0.9,
        source="assessment",
        evidence=["assessment-1"],
    )

    profile = await service.get("u1")
    assert profile is not None
    assert profile.version == 3
    assert len(profile.fields) == 1
    assert first.value == "engineering"
    assert second.value == "design"
    assert [field.key for field in await service.get_fields("u1", ["career_interest"])] == [
        "career_interest"
    ]
    assert await service.get_fields("u1", ["not_present"]) == []
    assert len(bus.events) == 2

    event = bus.events[-1]
    assert event.event_type == PROFILE_FIELD_UPDATED
    assert event.idempotency_key == event.event_id
    payload = ProfileFieldUpdatedPayload.model_validate(event.payload)
    assert payload.user_id == "u1"
    assert payload.field_key == "career_interest"
    assert payload.confidence == 0.9
    assert payload.source == "assessment"
    assert payload.profile_version == 3
    assert payload.updated_at == second.updated_at


async def test_invalid_field_does_not_write_or_publish(
    service: DefaultProfileService, bus: RecordingEventBus
) -> None:
    with pytest.raises(ValidationError):
        await service.update_field(
            "u1", "career_interest", "x", confidence=1.1, source="conversation"
        )
    with pytest.raises(ValidationError):
        await service.update_field(
            "u1", "career_interest", "x", confidence=0.5, source="unknown"
        )

    assert await service.get("u1") is None
    assert bus.events == []


async def test_replace_gaps(service: DefaultProfileService) -> None:
    gaps = [
        ProfileGap(
            key="real_constraint",
            reason="missing",
            suggested_next_action="ask",
        )
    ]
    await service.replace_gaps("u1", gaps)
    assert await service.get_gaps("u1") == gaps


async def test_confidence_uses_present_key_fields_only(
    service: DefaultProfileService,
) -> None:
    await service.update_field(
        "u1", "career_interest", "a", confidence=0.6, source="conversation"
    )
    await service.update_field(
        "u1", "ability_strength", "b", confidence=0.8, source="assessment"
    )
    await service.update_field(
        "u1", "non_key", "ignored", confidence=1.0, source="resume"
    )
    assert await service.overall_confidence("u1") == pytest.approx(0.7)


async def test_missing_or_invalid_confidence_params_fail_explicitly(
    repository: InMemoryProfileRepository, bus: RecordingEventBus, tmp_path: Path
) -> None:
    missing = DefaultProfileService(
        repository, LocalJsonRegistryRepository(str(tmp_path)), bus
    )
    with pytest.raises(ValueError, match="profile_collection"):
        await missing.overall_confidence("u1")

    class InvalidRegistry:
        async def get_policy_params(self, code: str):
            from zhiyin_kernel.registry import PolicyParamSet

            return PolicyParamSet(
                code=code, status="confirmed", value={"key_fields": []}
            )

    invalid = DefaultProfileService(repository, InvalidRegistry(), bus)
    with pytest.raises(ValueError, match="key_fields"):
        await invalid.overall_confidence("u1")


async def test_event_failure_is_visible_but_write_remains(
    repository: InMemoryProfileRepository, registry: LocalJsonRegistryRepository
) -> None:
    service = DefaultProfileService(
        repository, registry, RecordingEventBus(error=RuntimeError("publish failed"))
    )
    with pytest.raises(RuntimeError, match="publish failed"):
        await service.update_field(
            "u1", "career_interest", "a", confidence=0.7, source="conversation"
        )

    stored = await repository.get("u1")
    assert stored is not None
    assert [field.key for field in stored.fields] == ["career_interest"]


def test_profile_event_payload_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProfileFieldUpdatedPayload(
            user_id="u1",
            field_key="career_interest",
            confidence=0.7,
            source="conversation",
            profile_version=2,
            updated_at=datetime.now(timezone.utc),
            unexpected=True,
        )
