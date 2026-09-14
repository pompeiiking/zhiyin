"""业务层服务实现。

分工口径：

- `ports/` 放接口（冻结），`policies/` 放规则，`services/` 放**实现**；
- 从这里开始真正依赖 `zhiyin-orchestration`（AgentEngine / EventBus / Scheduler）
  与 `zhiyin-data-sdk`（Repository / Gateway）。

服务落位表（对应《第一期技术架构文档》§4.5.1 模块归属，一人一列互不阻塞）：

| 服务 | 文件 | 依赖 | 优先级 |
| --- | --- | --- | --- |
| Loop 协调器 | `loop.py`（已有参考实现） | AgentEngine、TaskSessionRepository | P0 |
| Orchestrator | `orchestrator.py` | 黑板四件套 + `policies/` + AgentEngine | P0 |
| Profile 服务 | `profile.py` | ProfileRepository、EventBus | P0 |
| Behavior 服务 | `behavior.py` | BehaviorRepository、EventBus | P0 |
| Memory 服务 | `memory.py` | ConversationMemoryRepository | P0 |
| Asset 服务 | `asset.py` | AssetRepository、EventBus + `policies/impact.py` | P0 |
| Workspace 服务 | `workspace.py` | 读侧聚合（Profile / Asset / Memory） | P1 |
| Function 服务 | `function.py` | ObjectStore、日历 | P1 |

目前提供的实现见各模块 docstring；业务线在既有实现上扩展，不要另起一套。
"""

from zhiyin_business.services.loop import (
    STAGE_OUTPUT_CONTRACTS,
    STAGE_SEQUENCE,
    AgentDrivenLoopCoordinator,
    default_conclusion_builder,
    next_stage_after,
)

__all__ = [
    "STAGE_OUTPUT_CONTRACTS",
    "STAGE_SEQUENCE",
    "AgentDrivenLoopCoordinator",
    "default_conclusion_builder",
    "next_stage_after",
]
