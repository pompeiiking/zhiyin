"""编排器实现（**骨架**，方法体未实现）。

落位：`business/services/orchestrator.py` —— 业务编排负责人。
依赖：黑板四件套 Port + `policies/` 四条规则 + AgentEngine + Registry / 会话 Repository。

实现前的前置条件（**未满足不要动手**）
------------------------------------
《技术架构文档》§十五 有 4 项口径直接阻塞本类，未定稿就只能靠猜，后续必返工：
1. 轴 A 阶段判定信号（`policies/teaming.py` 的 `LeadPolicy` 输入）；
2. 意图识别 → 环节判定的兜底规则（`policies/routing.py` 的 `StagePolicy`）；
3. 画像置信度算法与缺口表达（`COLLECT` 的交接判据）；
4. 主动干预参数：停滞阈值 / 冷却期 / 打扰上限（已在
   `data/registry/policy_params.json`，当前 `status=draft`）。

判据：这 4 项定稿后，本类只是"读黑板 → 调规则 → 落库 → 发事件"的装配式编排，
规则本身写在 `policies/`，**本类不得内联任何业务规则**。

`policies/` 里已有对应 ABC（`IntentPolicy` / `StagePolicy` / `LeadPolicy` /
`HandoffPolicy`），构造参数就是它们——规则实现与编排实现可以两个人并行做，
各自对着 ABC 交付。
"""

from __future__ import annotations

from zhiyin_business.policies.handoff import HandoffPolicy
from zhiyin_business.policies.routing import IntentPolicy, StagePolicy
from zhiyin_business.policies.teaming import LeadPolicy
from zhiyin_business.ports.blackboard import (
    AssetService,
    BehaviorService,
    BlackboardView,
    ConversationMemoryService,
    ProfileService,
)
from zhiyin_business.ports.orchestrator import (
    HandoffDecision,
    IntentType,
    LeadDecision,
    Orchestrator,
    StageDecision,
    TurnRequest,
    TurnResult,
)
from zhiyin_data_sdk.repositories import RegistryRepository, TaskSessionRepository
from zhiyin_kernel.enums import AxisAStage, LoopStage
from zhiyin_orchestration import AgentEngine, EventBus

_TODO = "TODO(骨架): Orchestrator 未实现"


class DefaultOrchestrator(Orchestrator):
    """编排器默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(
        self,
        *,
        profiles: ProfileService,
        behaviors: BehaviorService,
        memories: ConversationMemoryService,
        assets: AssetService,
        intent_policy: IntentPolicy,
        stage_policy: StagePolicy,
        lead_policy: LeadPolicy,
        handoff_policy: HandoffPolicy,
        agent_engine: AgentEngine,
        sessions: TaskSessionRepository,
        registry: RegistryRepository,
        event_bus: EventBus,
    ) -> None:
        self._profiles = profiles
        self._behaviors = behaviors
        self._memories = memories
        self._assets = assets
        self._intent_policy = intent_policy
        self._stage_policy = stage_policy
        self._lead_policy = lead_policy
        self._handoff_policy = handoff_policy
        self._agent_engine = agent_engine
        self._sessions = sessions
        self._registry = registry
        self._event_bus = event_bus

    async def read_blackboard(self, user_id: str, task_id: str) -> BlackboardView:
        raise NotImplementedError(f"{_TODO}：读黑板（画像 + 行为日志 + 会话记忆 + 资产版本）")

    async def detect_intent(self, user_id: str, message: str) -> IntentType:
        raise NotImplementedError(f"{_TODO}：调 IntentPolicy 识别意图")

    async def detect_stage(
        self, user_id: str, task_id: str, intent: IntentType
    ) -> StageDecision:
        raise NotImplementedError(
            f"{_TODO}：调 StagePolicy 判定环节；不确定时必须回澄清追问，不得硬跳"
        )

    async def infer_axis_a(self, user_id: str, task_id: str) -> AxisAStage:
        raise NotImplementedError(f"{_TODO}：规则优先 + LLM 兜底推断轴 A 阶段")

    async def select_lead(
        self,
        user_id: str,
        task_id: str,
        axis_a: AxisAStage,
        stage: LoopStage,
        intent: IntentType,
    ) -> LeadDecision:
        raise NotImplementedError(f"{_TODO}：调 LeadPolicy 选主理 / 协理 / 信息侦查员")

    async def handoff(
        self, user_id: str, task_id: str, to_stage: LoopStage, reason: str
    ) -> HandoffDecision:
        raise NotImplementedError(
            f"{_TODO}：调 HandoffPolicy；换主理必须产出 disclosure，为空即违规"
        )

    async def handle_message(self, request: TurnRequest) -> TurnResult:
        raise NotImplementedError(f"{_TODO}：单轮回复骨架（读黑板→判环节→选主理→产出→引导）")


__all__ = ["DefaultOrchestrator"]
