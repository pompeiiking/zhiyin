"""业务层服务实现。

分工口径：

- `ports/` 放接口（冻结），`policies/` 放规则，`services/` 放**实现**；
- 从这里开始真正依赖 `zhiyin-orchestration`（AgentEngine / EventBus / Scheduler）
  与 `zhiyin-data-sdk`（Repository / Gateway）。

服务落位表（对应《第一期技术架构文档》§4.5.1 模块归属，一人一列互不阻塞）。
**每个格子现在都是一个真实文件**：类骨架已就位、签名已按 Port 冻结、方法体
`raise NotImplementedError`。实现方只填方法体，不需要新建文件、不需要改装配表。
骨架的 `IMPLEMENTATION_STATUS = "skeleton"` 会被装配报告如实标为 skeleton，
因此"文件存在"不会被误读成"能力已具备"。

| 服务 | 文件 | 类 | 依赖 | 优先级 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Loop 协调器 | `loop.py` | `AgentDrivenLoopCoordinator` | AgentEngine、TaskSessionRepository | P0 | 参考实现 |
| Orchestrator | `orchestrator.py` | `DefaultOrchestrator` | 黑板四件套 + `policies/` + AgentEngine | P0 | 骨架 |
| Profile 服务 | `profile.py` | `DefaultProfileService` | ProfileRepository、EventBus | P0 | 骨架 |
| Behavior 服务 | `behavior.py` | `DefaultBehaviorService` | BehaviorRepository、EventBus | P0 | 骨架 |
| Memory 服务 | `memory.py` | `DefaultConversationMemoryService` | ConversationMemoryRepository | P0 | 骨架 |
| Asset 服务 | `asset.py` | `DefaultAssetService` | AssetRepository、EventBus + `policies/impact.py` | P0 | 骨架 |
| Workspace 服务 | `workspace.py` | `DefaultWorkspaceService` | 读侧聚合（Profile / Asset / Memory） | P1 | 骨架 |
| Function 服务 | `function.py` | `DefaultFunctionService` | ObjectStore、日历 | P1 | 骨架 |
| Identity 服务 | `identity.py` | `DefaultIdentityService` | AuthGateway、UserRepository | P0 | 骨架 |
| Registry 服务 | `registry.py` | `DefaultRegistryService` | RegistryRepository、FeatureFlagGateway | P0 | 骨架 |

> Identity 服务是 api 与数据访问契约之间的通道之一：api 层被禁止 import
> `zhiyin_data_sdk`，因此 Facade 拿不到 `AuthGateway`；由本服务把它包成业务 Port
> （`business/ports/identity.py::IdentityService`）。它是 Facade 的硬前置——
> Facade 一装配就会调它。

> Registry 服务是同一类问题的第二个通道（`business/ports/registry.py`）：
> `/app/bootstrap` 需要的菜单 / 路由 / 任务入口 / 文案 / 功能开关全在动态资源里，
> 而取数契约在 `zhiyin_data_sdk`，api 同样拿不到。它是 Facade 的另一个硬前置。
> 两条通道的分工：Identity 管"我是谁"，Registry 管"页面长什么样"。

实现顺序建议：黑板四件套（Profile / Behavior / Memory / Asset）→ Identity + Registry
（这两个是 Facade 的硬前置，Facade 一装配就会调它们）→ Facade（前端随即可以联调）
→ Orchestrator → Workspace / Function。Orchestrator 的前置是《技术架构文档》§十五 的
4 项口径定稿，未定稿不要动手（见 `orchestrator.py` 的 docstring）。
"""

from zhiyin_business.services.loop import (
    STAGE_OUTPUT_CONTRACTS,
    STAGE_SEQUENCE,
    AgentDrivenLoopCoordinator,
    default_conclusion_builder,
    next_stage_after,
)
from zhiyin_business.services.asset import DefaultAssetService
from zhiyin_business.services.behavior import DefaultBehaviorService
from zhiyin_business.services.function import DefaultFunctionService
from zhiyin_business.services.identity import DefaultIdentityService
from zhiyin_business.services.memory import DefaultConversationMemoryService
from zhiyin_business.services.orchestrator import DefaultOrchestrator
from zhiyin_business.services.profile import DefaultProfileService
from zhiyin_business.services.registry import DefaultRegistryService
from zhiyin_business.services.workspace import DefaultWorkspaceService

__all__ = [
    "STAGE_OUTPUT_CONTRACTS",
    "STAGE_SEQUENCE",
    "AgentDrivenLoopCoordinator",
    "DefaultAssetService",
    "DefaultBehaviorService",
    "DefaultConversationMemoryService",
    "DefaultFunctionService",
    "DefaultIdentityService",
    "DefaultOrchestrator",
    "DefaultProfileService",
    "DefaultRegistryService",
    "DefaultWorkspaceService",
    "default_conclusion_builder",
    "next_stage_after",
]
