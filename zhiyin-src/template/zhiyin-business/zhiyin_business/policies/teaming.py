"""动态组队规则：选主理 / 协理 / 信息侦查员（轴 A × 轴 B × 意图）。

对应 FR-ORCH-002。产品主线要求"现在是谁在帮我、依据什么"必须能回答，
因此规则产出的 `LeadDecision.reason` 会被直接用于界面上的显式告知。

轴 A 口径已定稿（《业务口径决策记录-v1.0》决策 1/2/3）：
五段全量、规则优先 + LLM 兜底、单轨 + 会话路径焦点。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import IntentType, LeadDecision
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.enums import AxisAStage, LoopStage


class LeadPolicy(ABC):
    """主理选择规则。"""

    @abstractmethod
    async def select(
        self,
        *,
        blackboard: BlackboardView,
        axis_a: AxisAStage,
        stage: LoopStage,
        intent: IntentType,
    ) -> LeadDecision:
        """选择主理（及协理 / 信息侦查员）。

        约束：
        - 主理必须来自 `AgentRegistry`（动态资源），不得在代码里写死 agent_id；
        - 同一环节不同轴 A 阶段可以选不同主理，这是"同一环节不同服务深度"的落点；
        - `reason` 是给用户看的依据，不是内部日志。
        """


class RegistryLeadPolicy(LeadPolicy):
    """从动态任务入口推导环节主理，不在业务代码固化 agent_id。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, registry: RegistryRepository) -> None:
        self._registry = registry

    async def select(
        self,
        *,
        blackboard: BlackboardView,
        axis_a: AxisAStage,
        stage: LoopStage,
        intent: IntentType,
    ) -> LeadDecision:
        entries = await self._registry.list_task_entries()
        lead_agent = next(
            (
                entry.lead_agent
                for entry in entries
                if entry.target_stage is stage and entry.lead_agent is not None
            ),
            None,
        )
        if lead_agent is None:
            raise LookupError(f"动态资源未配置环节主理：{stage.value}")
        return LeadDecision(
            lead_agent=lead_agent,
            assistant_agents=[],
            info_scout_required=intent is IntentType.VERIFY_DIRECTION,
            reason=f"当前需求属于{stage.value}环节，由该环节配置的主理继续服务",
        )


__all__ = ["LeadPolicy", "RegistryLeadPolicy"]
