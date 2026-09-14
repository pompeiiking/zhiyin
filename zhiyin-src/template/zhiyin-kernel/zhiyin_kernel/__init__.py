"""zhiyin-kernel · 共享内核（shared kernel）。

本包是全系统**唯一**的"数据形状"定义处：跨层枚举、身份、黑板数据形状、
资产数据形状、动态资源形状。它横切全部层，因此：

- **零依赖**：不得 import 任何其它 `zhiyin_*` 包（含 data-sdk / business），
  由 `tests/test_architecture.py::test_kernel_has_no_dependencies` 守卫；
- **无行为**：只允许声明数据形状与纯函数式取值，不得写业务逻辑、不得访问 IO；
- 所有层都可以读它，但任何层都不得在这里扩展业务语义。

它曾经叫 `zhiyin_data_sdk.contracts`，名字挂在数据访问包下，导致两处失真：
新人会把 `Profile` / `AssetVersion` 这类领域模型误当成数据访问契约；业务模型
一旦调整就要跨包改动。现在改名归位为独立内核。

历史缺陷（不再回退）：曾出现 `zhiyin-api` 直接 import
`zhiyin_data_sdk.contracts.enums` 的越层依赖，由本包改名后按矩阵放行 api → kernel。

约束：
- DTO 不得直接暴露数据库实体（R-API-007），数据库实体只在 infrastructure
  的 persistence 层出现。
"""

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
from zhiyin_kernel.blackboard import (
    AssetVersion,
    BehaviorLog,
    ConversationMemory,
    Profile,
    ProfileField,
    ProfileGap,
    TaskSession,
)
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
    Swot,
    TrackEvent,
    Verdict,
)
from zhiyin_kernel.identity import (
    AuthSession,
    GuestSession,
    ProfileSummary,
    UserAccount,
)
from zhiyin_kernel.registry import (
    AgentDescriptor,
    OutputContractSpec,
    TaskEntrySpec,
    TheoryCard,
)

__all__ = [
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
    "AssetVersion",
    "BehaviorLog",
    "ConversationMemory",
    "Profile",
    "ProfileField",
    "ProfileGap",
    "TaskSession",
    "ActionPhase",
    "ActionPlan",
    "ActionTask",
    "Achievement",
    "DirectionPlan",
    "GapClaim",
    "PlanGap",
    "Report",
    "ReportDimensionGroup",
    "ReportDimensionItem",
    "Swot",
    "TrackEvent",
    "Verdict",
    "AuthSession",
    "GuestSession",
    "ProfileSummary",
    "UserAccount",
    "AgentDescriptor",
    "OutputContractSpec",
    "TaskEntrySpec",
    "TheoryCard",
]
