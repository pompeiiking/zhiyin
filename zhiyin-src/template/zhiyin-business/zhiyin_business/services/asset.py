"""资产服务实现（**骨架**，方法体未实现）。

落位：`business/services/asset.py` —— 业务编排负责人。
依赖：`AssetRepository` + `EventBus` + `policies/impact.py`。

核心口径（R-BIZ-012）：画像字段更新 → 只重算**受影响的**资产片段 → 版本 +1 → 写 diff。
**禁止整篇重新生成。** 重算范围的判定在 `ImpactPolicy`，本类只负责执行与落库；
"哪些字段影响哪些资产"不进本文件。
"""

from __future__ import annotations

from typing import Optional, Sequence

from zhiyin_business.contracts.common import AssetUpdateDraft
from zhiyin_business.policies.impact import ImpactPolicy
from zhiyin_business.ports.blackboard import AssetService
from zhiyin_data_sdk.repositories import AssetRepository
from zhiyin_kernel.assets import ActionPlan, DirectionPlan, Report
from zhiyin_kernel.blackboard import AssetVersion
from zhiyin_kernel.enums import AssetType
from zhiyin_orchestration import EventBus

_TODO = "TODO(骨架): AssetService 未实现"


class DefaultAssetService(AssetService):
    """资产服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(
        self,
        assets: AssetRepository,
        event_bus: EventBus,
        impact_policy: ImpactPolicy,
    ) -> None:
        self._assets = assets
        self._event_bus = event_bus
        self._impact_policy = impact_policy

    async def list_versions(self, user_id: str, asset_type: AssetType) -> list[AssetVersion]:
        raise NotImplementedError(f"{_TODO}：列出某类资产的历史版本")

    async def propagate(
        self, user_id: str, changed_profile_keys: Sequence[str]
    ) -> list[AssetVersion]:
        raise NotImplementedError(
            f"{_TODO}：影响面传播（用 ImpactPolicy 选范围，只重算命中片段，版本 +1）"
        )

    async def save_version(self, user_id: str, draft: AssetUpdateDraft) -> AssetVersion:
        raise NotImplementedError(f"{_TODO}：保存新版本 + 发 asset_version_changed")

    async def get_report(self, user_id: str, version: Optional[int] = None) -> Optional[Report]:
        raise NotImplementedError(f"{_TODO}：读诊断报告全文")

    async def list_direction_plans(self, user_id: str) -> list[DirectionPlan]:
        raise NotImplementedError(f"{_TODO}：读主攻 / 平行 / 保底三套方案")

    async def get_action_plan(self, user_id: str) -> Optional[ActionPlan]:
        raise NotImplementedError(f"{_TODO}：读行动计划")


__all__ = ["DefaultAssetService"]
