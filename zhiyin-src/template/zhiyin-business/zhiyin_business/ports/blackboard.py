"""黑板服务契约。

黑板 = 共享状态（PRD §3.3）：
1. 个人画像（活状态：字段值 + 置信度 + 缺口 + 更新时间线）
2. 行为日志（事件流）
3. 会话记忆（各任务会话摘要）
4. 资产版本与影响面

本模块只定义读写接口与只读视图，不承载跨环节编排逻辑（那属于 Orchestrator /
LoopCoordinator）。所有智能体读写同一份黑板。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.assets import (
    ActionPlan,
    DirectionPlan,
    Report,
)
from zhiyin_kernel.blackboard import (
    AssetVersion,
    BehaviorLog,
    ConversationMemory,
    Profile,
    ProfileField,
    ProfileGap,
)
from zhiyin_kernel.enums import AssetType, BehaviorEventType, LoopStage
from zhiyin_business.contracts.common import (
    AssetUpdateDraft,
    BehaviorEventDraft,
)


class BlackboardView(BaseModel):
    """黑板的只读快照。

    每次回复的第一步都是"读黑板"（FR-ORCH-006）；所有智能体共享同一份。
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    task_id: Optional[str] = None
    profile: Optional[Profile] = Field(default=None, description="画像活状态")
    recent_behaviors: list[BehaviorLog] = Field(
        default_factory=list, description="近期行为日志，按时间倒序"
    )
    memories: list[ConversationMemory] = Field(default_factory=list)
    asset_versions: list[AssetVersion] = Field(default_factory=list)
    current_stage: Optional[LoopStage] = None


class ProfileService(ABC):
    """画像活状态读写（FR-COLLECT-003 / R-BIZ-006）。"""

    @abstractmethod
    async def get(self, user_id: str) -> Optional[Profile]:
        """读取完整画像。"""

    @abstractmethod
    async def get_fields(
        self, user_id: str, keys: Optional[Sequence[str]] = None
    ) -> list[ProfileField]:
        """按字段键读取画像字段，用于提示词注入与影响面判定。"""

    @abstractmethod
    async def get_gaps(self, user_id: str) -> list[ProfileGap]:
        """读取缺口清单，用于采集追问与工作台展示（FR-COLLECT-002）。"""

    @abstractmethod
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
        """更新单个画像字段。

        必须发布 profile_field_updated 事件，触发影响面传播（FR-ORCH-004）。
        """

    @abstractmethod
    async def replace_gaps(self, user_id: str, gaps: list[ProfileGap]) -> None:
        """整体替换缺口清单。"""

    @abstractmethod
    async def overall_confidence(self, user_id: str) -> float:
        """画像整体置信度。采集环节的结束条件依据（FR-COLLECT-007）。"""


class BehaviorService(ABC):
    """行为日志写入与查询（FR-REVIEW-007）。"""

    @abstractmethod
    async def log(self, user_id: str, draft: BehaviorEventDraft) -> BehaviorLog:
        """写入一条行为日志，并发布 behavior_logged 事件。"""

    @abstractmethod
    async def recent(
        self,
        user_id: str,
        *,
        event_types: Optional[Sequence[BehaviorEventType]] = None,
        limit: int = 50,
    ) -> list[BehaviorLog]:
        """读取近期行为日志。"""

    @abstractmethod
    async def days_since_last(
        self, user_id: str, event_type: BehaviorEventType
    ) -> Optional[int]:
        """距某类行为发生过了几天。停滞检测的唯一依据（FR-REVIEW-001）。"""


class ConversationMemoryService(ABC):
    """会话记忆读写（跨会话续接 / FR-ORCH-005）。"""

    @abstractmethod
    async def get(self, user_id: str, task_id: str) -> Optional[ConversationMemory]:
        """读取会话记忆。"""

    @abstractmethod
    async def upsert(
        self,
        user_id: str,
        task_id: str,
        *,
        loop_stage: LoopStage,
        lead_agent: str,
        summary_delta: str = "",
    ) -> ConversationMemory:
        """更新会话记忆（追加摘要片段）。"""

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[ConversationMemory]:
        """列出用户全部任务会话记忆。"""


class AssetService(ABC):
    """资产版本与影响面（FR-ORCH-004 / R-BIZ-012）。

    核心规则：画像字段更新 → 只重算受影响片段 → 版本 +1 → 写 diff。
    禁止整篇重新生成。
    """

    @abstractmethod
    async def list_versions(self, user_id: str, asset_type: AssetType) -> list[AssetVersion]:
        """列出某类资产的历史版本。"""

    @abstractmethod
    async def propagate(self, user_id: str, changed_profile_keys: Sequence[str]) -> list[AssetVersion]:
        """影响面传播。

        由 profile_field_updated 事件触发；返回本轮版本发生变化的资产列表。
        """

    @abstractmethod
    async def save_version(
        self, user_id: str, draft: AssetUpdateDraft
    ) -> AssetVersion:
        """保存一次新版本并发布 asset_version_changed 事件。"""

    @abstractmethod
    async def save_report(
        self,
        user_id: str,
        report: Report,
        *,
        depends_on_profile_keys: Sequence[str] = (),
        reason: str = "",
    ) -> AssetVersion:
        """保存报告正文及对应版本元数据。"""

    @abstractmethod
    async def save_direction_plans(
        self,
        user_id: str,
        plans: list[DirectionPlan],
        *,
        depends_on_profile_keys: Sequence[str] = (),
        reason: str = "",
    ) -> AssetVersion:
        """整体保存方向方案组及对应版本元数据。"""

    @abstractmethod
    async def select_direction_plan(self, user_id: str, plan_id: str) -> DirectionPlan:
        """选择或重选方向方案。"""

    @abstractmethod
    async def save_action_plan(
        self,
        user_id: str,
        plan: ActionPlan,
        *,
        depends_on_profile_keys: Sequence[str] = (),
        reason: str = "",
    ) -> AssetVersion:
        """保存行动计划及对应版本元数据。"""

    @abstractmethod
    async def mark_task_done(self, user_id: str, task_id: str) -> ActionPlan:
        """幂等完成行动任务。"""

    # ---------- 资产内容读取（供工作台 / 报告页） ----------

    @abstractmethod
    async def get_report(self, user_id: str, version: Optional[int] = None) -> Optional[Report]:
        """读取诊断报告全文。"""

    @abstractmethod
    async def claim_gap(self, user_id: str, gap_id: str) -> Report:
        """认领最新一版报告中的一条差距（FR-DIAG-004）。

        幂等；认领只追加认领记录，不重算正文、不产生新版本。
        """

    @abstractmethod
    async def list_direction_plans(self, user_id: str) -> list[DirectionPlan]:
        """读取主攻/平行/保底方案。"""

    @abstractmethod
    async def get_action_plan(self, user_id: str) -> Optional[ActionPlan]:
        """读取行动计划。"""
