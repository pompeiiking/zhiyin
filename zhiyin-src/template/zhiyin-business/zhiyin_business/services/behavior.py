"""行为日志服务实现（**骨架**，方法体未实现）。

落位：`business/services/behavior.py` —— 业务编排负责人。
依赖：`BehaviorRepository` + `EventBus`。

行为日志是北极星指标与主动干预的唯一事实来源，因此两条约束：
- 只追加，不提供任何修改路径（Repository 契约已保证，本类不得绕过）；
- 写入后必须发 `behavior_logged`，成就解锁与停滞检测都挂在它上面。
"""

from __future__ import annotations

from typing import Optional, Sequence

from zhiyin_business.contracts.common import BehaviorEventDraft
from zhiyin_business.ports.blackboard import BehaviorService
from zhiyin_data_sdk.repositories import BehaviorRepository
from zhiyin_kernel.blackboard import BehaviorLog
from zhiyin_kernel.enums import BehaviorEventType
from zhiyin_orchestration import EventBus

_TODO = "TODO(骨架): BehaviorService 未实现"


class DefaultBehaviorService(BehaviorService):
    """行为日志服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, behaviors: BehaviorRepository, event_bus: EventBus) -> None:
        self._behaviors = behaviors
        self._event_bus = event_bus

    async def log(self, user_id: str, draft: BehaviorEventDraft) -> BehaviorLog:
        raise NotImplementedError(f"{_TODO}：落库 + 发 behavior_logged")

    async def recent(
        self,
        user_id: str,
        *,
        event_types: Optional[Sequence[BehaviorEventType]] = None,
        limit: int = 50,
    ) -> list[BehaviorLog]:
        raise NotImplementedError(f"{_TODO}：按时间倒序读近期行为")

    async def days_since_last(
        self, user_id: str, event_type: BehaviorEventType
    ) -> Optional[int]:
        raise NotImplementedError(f"{_TODO}：距某类行为过了几天（停滞检测的唯一依据）")


__all__ = ["DefaultBehaviorService"]
