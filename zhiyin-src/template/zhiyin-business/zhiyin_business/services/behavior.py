"""行为日志服务实现。

落位：`business/services/behavior.py` —— 业务编排负责人。
依赖：`BehaviorRepository` + `EventBus`。

行为日志是北极星指标与主动干预的唯一事实来源，因此两条约束：
- 只追加，不提供任何修改路径（Repository 契约已保证，本类不得绕过）；
- 写入后必须发 `behavior_logged`，成就解锁与停滞检测都挂在它上面。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import uuid4

from zhiyin_business.contracts.common import BehaviorEventDraft
from zhiyin_business.events import BEHAVIOR_LOGGED
from zhiyin_business.ports.blackboard import BehaviorService
from zhiyin_data_sdk.repositories import BehaviorRepository
from zhiyin_kernel.blackboard import BehaviorLog
from zhiyin_kernel.enums import BehaviorEventType
from zhiyin_orchestration import DomainEvent, EventBus


class DefaultBehaviorService(BehaviorService):
    """行为日志服务默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, behaviors: BehaviorRepository, event_bus: EventBus) -> None:
        self._behaviors = behaviors
        self._event_bus = event_bus

    async def log(self, user_id: str, draft: BehaviorEventDraft) -> BehaviorLog:
        stored = await self._behaviors.append(
            BehaviorLog(
                id=f"bhv_{uuid4().hex[:12]}",
                user_id=user_id,
                event_type=draft.event_type,
                occurred_at=datetime.now(timezone.utc),
                payload=draft.payload,
                related_asset_ids=draft.related_asset_ids,
            )
        )
        await self._event_bus.publish(
            DomainEvent(
                event_id=f"evt_{uuid4().hex}",
                event_type=BEHAVIOR_LOGGED,
                occurred_at=stored.occurred_at,
                payload=stored.model_dump(mode="json"),
                idempotency_key=f"behavior:{stored.id}",
            )
        )
        return stored

    async def recent(
        self,
        user_id: str,
        *,
        event_types: Optional[Sequence[BehaviorEventType]] = None,
        limit: int = 50,
    ) -> list[BehaviorLog]:
        return await self._behaviors.list_by_user(
            user_id, event_types=event_types, limit=max(limit, 0)
        )

    async def days_since_last(
        self, user_id: str, event_type: BehaviorEventType
    ) -> Optional[int]:
        occurred_at = await self._behaviors.last_occurred_at(user_id, event_type)
        if occurred_at is None:
            return None
        current = datetime.now(timezone.utc)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        return max((current - occurred_at).days, 0)


__all__ = ["DefaultBehaviorService"]
