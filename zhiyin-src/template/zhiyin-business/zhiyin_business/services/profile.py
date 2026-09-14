"""画像服务实现（**骨架**，方法体未实现）。

落位：`business/services/profile.py` —— 业务编排负责人。
依赖：`ProfileRepository` + `EventBus`。

本类只做"画像活状态的读写与事件发布"，**不含**采集话术与置信度算法：
- 字段结构与置信度取值 → `zhiyin_kernel.blackboard.ProfileField` + 业务规则；
- 画像 → 资产的影响面判定 → `policies/impact.py`（本类只负责发
  `profile_field_updated` 事件，不直接改资产）。

硬约束：`update_field` **必须**发布 `profile_field_updated`（FR-ORCH-004 的触发点），
否则影响面传播整条链路不会启动，且失败是静默的。
"""

from __future__ import annotations

from typing import Optional, Sequence

from zhiyin_business.ports.blackboard import ProfileService
from zhiyin_data_sdk.repositories import ProfileRepository
from zhiyin_kernel.blackboard import Profile, ProfileField, ProfileGap
from zhiyin_orchestration import EventBus

_TODO = "TODO(骨架): ProfileService 未实现"


class DefaultProfileService(ProfileService):
    """画像服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, profiles: ProfileRepository, event_bus: EventBus) -> None:
        self._profiles = profiles
        self._event_bus = event_bus

    async def get(self, user_id: str) -> Optional[Profile]:
        raise NotImplementedError(f"{_TODO}：读完整画像")

    async def get_fields(
        self, user_id: str, keys: Optional[Sequence[str]] = None
    ) -> list[ProfileField]:
        raise NotImplementedError(f"{_TODO}：按 key 批量读画像字段")

    async def get_gaps(self, user_id: str) -> list[ProfileGap]:
        raise NotImplementedError(f"{_TODO}：读缺口清单")

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
        raise NotImplementedError(
            f"{_TODO}：写字段 + 发 profile_field_updated（少了事件，影响面传播静默失效）"
        )

    async def replace_gaps(self, user_id: str, gaps: list[ProfileGap]) -> None:
        raise NotImplementedError(f"{_TODO}：整体替换缺口清单")

    async def overall_confidence(self, user_id: str) -> float:
        raise NotImplementedError(f"{_TODO}：整体置信度（采集结束判据，口径待业务定稿）")


__all__ = ["DefaultProfileService"]
