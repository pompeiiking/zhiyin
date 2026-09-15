"""行为日志服务的业务行为测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from zhiyin_business.contracts.common import BehaviorEventDraft
from zhiyin_business.events import BEHAVIOR_LOGGED, BehaviorLoggedPayload
from zhiyin_business.services.behavior import DefaultBehaviorService
from zhiyin_infrastructure.local.repository import InMemoryBehaviorRepository
from zhiyin_kernel.blackboard import BehaviorLog
from zhiyin_kernel.enums import BehaviorEventType
from zhiyin_orchestration import DomainEvent, EventBus


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
def repository() -> InMemoryBehaviorRepository:
    return InMemoryBehaviorRepository()


@pytest.fixture
def bus() -> RecordingEventBus:
    return RecordingEventBus()


@pytest.fixture
def service(repository, bus) -> DefaultBehaviorService:
    return DefaultBehaviorService(repository, bus)


@pytest.mark.parametrize("event_type", list(BehaviorEventType))
async def test_log_supports_every_event_type(
    service: DefaultBehaviorService,
    bus: RecordingEventBus,
    event_type: BehaviorEventType,
) -> None:
    stored = await service.log(
        "u1",
        BehaviorEventDraft(
            event_type=event_type,
            payload={"source": "test"},
            related_asset_ids=["asset-1"],
        ),
    )

    assert stored.id
    assert stored.event_type == event_type
    event = bus.events[-1]
    assert event.event_type == BEHAVIOR_LOGGED
    assert event.idempotency_key == event.event_id
    payload = BehaviorLoggedPayload.model_validate(event.payload)
    assert payload.user_id == "u1"
    assert payload.behavior_log_id == stored.id
    assert payload.behavior_event_type == event_type
    assert payload.occurred_at == stored.occurred_at
    assert payload.payload == {"source": "test"}
    assert payload.related_asset_ids == ["asset-1"]


async def test_recent_is_append_only_filtered_desc_and_limited(
    service: DefaultBehaviorService,
) -> None:
    first = await service.log(
        "u1", BehaviorEventDraft(event_type=BehaviorEventType.ANSWER)
    )
    second = await service.log(
        "u1", BehaviorEventDraft(event_type=BehaviorEventType.REVIEW)
    )
    third = await service.log(
        "u1", BehaviorEventDraft(event_type=BehaviorEventType.ANSWER)
    )
    await service.log("u2", BehaviorEventDraft(event_type=BehaviorEventType.ANSWER))

    assert [item.id for item in await service.recent("u1")] == [
        third.id,
        second.id,
        first.id,
    ]
    assert [
        item.id
        for item in await service.recent(
            "u1", event_types=[BehaviorEventType.ANSWER], limit=1
        )
    ] == [third.id]
    assert await service.recent("u1", limit=0) == []

    snapshot = await service.recent("u1")
    snapshot[0].payload["changed"] = True
    assert "changed" not in (await service.recent("u1"))[0].payload


async def test_negative_limit_is_rejected_without_querying(
    service: DefaultBehaviorService,
) -> None:
    with pytest.raises(ValueError, match="limit"):
        await service.recent("u1", limit=-1)


async def test_days_since_last_handles_missing_past_and_future(
    repository: InMemoryBehaviorRepository, service: DefaultBehaviorService
) -> None:
    assert await service.days_since_last("u1", BehaviorEventType.ANSWER) is None

    await repository.append(
        BehaviorLog(
            id="past",
            user_id="u1",
            event_type=BehaviorEventType.ANSWER,
            occurred_at=datetime.now(timezone.utc) - timedelta(days=3, minutes=1),
        )
    )
    assert await service.days_since_last("u1", BehaviorEventType.ANSWER) == 3

    await repository.append(
        BehaviorLog(
            id="future",
            user_id="u1",
            event_type=BehaviorEventType.REVIEW,
            occurred_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    assert await service.days_since_last("u1", BehaviorEventType.REVIEW) == 0


async def test_naive_timestamp_is_treated_as_utc(
    repository: InMemoryBehaviorRepository, service: DefaultBehaviorService
) -> None:
    await repository.append(
        BehaviorLog(
            id="naive",
            user_id="u1",
            event_type=BehaviorEventType.ANSWER,
            occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    assert await service.days_since_last("u1", BehaviorEventType.ANSWER) == 0


async def test_event_failure_is_visible_but_append_remains(
    repository: InMemoryBehaviorRepository,
) -> None:
    service = DefaultBehaviorService(
        repository, RecordingEventBus(error=RuntimeError("publish failed"))
    )
    with pytest.raises(RuntimeError, match="publish failed"):
        await service.log(
            "u1", BehaviorEventDraft(event_type=BehaviorEventType.TASK_DONE)
        )

    stored = await repository.list_by_user("u1")
    assert len(stored) == 1
    assert stored[0].event_type == BehaviorEventType.TASK_DONE


def test_behavior_event_payload_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BehaviorLoggedPayload(
            user_id="u1",
            behavior_log_id="log-1",
            behavior_event_type=BehaviorEventType.ANSWER,
            occurred_at=datetime.now(timezone.utc),
            payload={},
            related_asset_ids=[],
            unexpected=True,
        )
