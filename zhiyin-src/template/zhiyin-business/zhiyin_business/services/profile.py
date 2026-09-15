"""画像服务实现。

落位：`business/services/profile.py` —— 业务编排负责人。
依赖：`ProfileRepository` + `RegistryRepository` + `EventBus`。

本类只做"画像活状态的读写与事件发布"，**不含**采集话术与置信度算法：
- 字段结构与置信度取值 → `zhiyin_kernel.blackboard.ProfileField` + 业务规则；
- 画像 → 资产的影响面判定 → `policies/impact.py`（本类只负责发
  `profile_field_updated` 事件，不直接改资产）。

硬约束：`update_field` **必须**发布 `profile_field_updated`（FR-ORCH-004 的触发点），
否则影响面传播整条链路不会启动，且失败是静默的。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from zhiyin_business.events import (
    PROFILE_FIELD_UPDATED,
    ProfileFieldUpdatedPayload,
)
from zhiyin_business.policies.profile import (
    PROFILE_COLLECTION_POLICY,
    calculate_overall_confidence,
)
from zhiyin_business.ports.blackboard import ProfileService
from zhiyin_data_sdk.repositories import ProfileRepository, RegistryRepository
from zhiyin_kernel.blackboard import Profile, ProfileField, ProfileGap
from zhiyin_orchestration import DomainEvent, EventBus


class DefaultProfileService(ProfileService):
    """画像服务默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        profiles: ProfileRepository,
        registry: RegistryRepository,
        event_bus: EventBus,
    ) -> None:
        self._profiles = profiles
        self._registry = registry
        self._event_bus = event_bus

    async def get(self, user_id: str) -> Optional[Profile]:
        return await self._profiles.get(user_id)

    async def get_fields(
        self, user_id: str, keys: Optional[Sequence[str]] = None
    ) -> list[ProfileField]:
        return await self._profiles.list_fields(user_id, keys)

    async def get_gaps(self, user_id: str) -> list[ProfileGap]:
        return await self._profiles.list_gaps(user_id)

    async def update_field(
        self,
        user_id: str,
        key: str,
        value: object,
        *,
        confidence: float,
        source: str,
        evidence: Optional[list[str]] = None,
    ) -> ProfileField:
        field = ProfileField(
            key=key,
            value=value,
            confidence=confidence,
            source=source,
            evidence=list(evidence or ()),
            updated_at=datetime.now(timezone.utc),
        )
        stored = await self._profiles.upsert_field(user_id, field)

        profile = await self._profiles.get(user_id)
        if profile is None:
            raise RuntimeError("画像字段写入成功后无法读取画像版本")

        event_key = (
            f"{PROFILE_FIELD_UPDATED}:{profile.id}:{profile.version}:{stored.key}"
        )
        payload = ProfileFieldUpdatedPayload(
            user_id=user_id,
            field_key=stored.key,
            confidence=stored.confidence,
            source=stored.source.value,
            profile_version=profile.version,
            updated_at=stored.updated_at,
        )
        await self._event_bus.publish(
            DomainEvent(
                event_id=event_key,
                event_type=PROFILE_FIELD_UPDATED,
                occurred_at=stored.updated_at,
                payload=payload.model_dump(mode="json"),
                idempotency_key=event_key,
            )
        )
        return stored

    async def replace_gaps(self, user_id: str, gaps: list[ProfileGap]) -> None:
        await self._profiles.replace_gaps(user_id, gaps)

    async def overall_confidence(self, user_id: str) -> float:
        params = await self._registry.get_policy_params(PROFILE_COLLECTION_POLICY)
        if params is None:
            raise ValueError("缺少动态规则参数：profile_collection")
        fields = await self._profiles.list_fields(user_id)
        return calculate_overall_confidence(fields, params)


__all__ = ["DefaultProfileService"]
