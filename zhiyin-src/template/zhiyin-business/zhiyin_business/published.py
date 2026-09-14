"""业务逻辑层的**对外发布面**（published language）。

现状与定位
----------
共享形状（枚举 / 读模型 / 动态资源形状）已经归位到独立的零依赖内核
`zhiyin_kernel`，AST 守卫矩阵允许 api 直接读内核形状（api → business + kernel）。
本模块因此不再是"绕过越层限制的补丁"，而是**业务能力的对外声明面**：

- api 通过它拿到业务侧承诺稳定的读模型与取值口径；
- 业务内部模型（Port、policies、services 的实现类型）不进本模块；
- 未来契约变更时由本模块做**版本适配**，BFF 与前端不受内部重构影响
  （这也是 R-API-007「DTO 不得直接暴露数据库实体」的落地方式）。

约定
----
- 只再导出**读模型与枚举**，不再导出 Repository / Gateway 等数据访问契约。
- 新增对外可见的领域取值时，先加到这里，业务内部模型不进本模块。
"""

from zhiyin_kernel.assets import (
    ActionPhase,
    ActionPlan,
    ActionTask,
    Achievement,
    DirectionPlan,
    GapClaim,
    PlanGap,
    Report,
    ReportDimensionGroup,
    ReportDimensionItem,
    TrackEvent,
)
from zhiyin_kernel.blackboard import (
    AssetVersion,
    BehaviorLog,
    ConversationMemory,
    Profile,
    ProfileField,
    ProfileGap,
    TaskSession,
)
from zhiyin_kernel.enums import (
    AgentRole,
    AgentRuntimeStatus,
    AssetType,
    BehaviorEventType,
    LoopStage,
    NotifyChannel,
    PlanRole,
    ProfileSource,
    ReviewAttribution,
    TaskStatus,
    UserRole,
)
from zhiyin_kernel.registry import (
    AgentDescriptor,
    OutputContractSpec,
    TaskEntrySpec,
    TheoryCard,
)

__all__ = [
    # ---- 枚举 ----
    "AgentRole",
    "AgentRuntimeStatus",
    "AssetType",
    "BehaviorEventType",
    "LoopStage",
    "NotifyChannel",
    "PlanRole",
    "ProfileSource",
    "ReviewAttribution",
    "TaskStatus",
    "UserRole",
    # ---- 读模型 ----
    "ActionPhase",
    "ActionPlan",
    "ActionTask",
    "Achievement",
    "AssetVersion",
    "BehaviorLog",
    "ConversationMemory",
    "DirectionPlan",
    "GapClaim",
    "PlanGap",
    "Profile",
    "ProfileField",
    "ProfileGap",
    "Report",
    "ReportDimensionGroup",
    "ReportDimensionItem",
    "TaskSession",
    "TrackEvent",
    # ---- 动态资源形状 ----
    "AgentDescriptor",
    "OutputContractSpec",
    "TaskEntrySpec",
    "TheoryCard",
]
