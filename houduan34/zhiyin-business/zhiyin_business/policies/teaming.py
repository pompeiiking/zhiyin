"""动态组队规则：选主理 / 协理 / 信息侦查员（轴 A × 轴 B × 意图）—— 实现交付（第二波 · 后端-3）。

对应 FR-ORCH-002。产品主线要求"现在是谁在帮我、依据什么"必须能回答，
因此规则产出的 `LeadDecision.reason` 会被直接用于界面上的显式告知。

轴 A 口径已定稿（《业务口径决策记录-v1.0》决策 1/2/3）：
五段全量、规则优先 + LLM 兜底、单轨 + 会话路径焦点。

实现口径（对着已冻结 ABC 交付）：
- `RegistryLeadPolicy`：主理映射**全部来自动态资源**——`task_entries` 里每条
  入口声明的 `(target_stage, lead_agent)` 构成"环节 → 主理"索引，
  代码里不写死任何 agent_id；索引得到的 id 必须在 `agents.json` 已登记，
  否则响亮失败（静默回落比报错贵）；
- 轴 A 阶段当前不改变主理人选（动态资源尚未提供"环节 × 轴 A"的差异化声明），
  只进入 `reason` 依据；待动态资源扩展后在此处消费，不需要改调用方；
- 协理：黑板画像仍有缺口且主理不是建档分析师时，加建档分析师协理（补信息）；
- 信息侦查员：验证方向（VERIFY_DIRECTION）需要外部事实供给时按需标记，
  侦查员不参与结论（agents.json not_to_do）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import IntentType, LeadDecision
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.enums import (
    AgentRole,
    AgentRuntimeStatus,
    AxisAStage,
    LoopStage,
)


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
    """主理选择：环节 → 主理索引读自任务入口动态资源，协理按画像缺口与意图叠加。"""

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
        agents = {agent.id: agent for agent in await self._registry.list_agents()}

        # 1) "环节 → 主理"索引：来自任务入口声明（sort_order 升序取先声明者）。
        stage_lead: dict[LoopStage, str] = {}
        for entry in sorted(
            await self._registry.list_task_entries(), key=lambda e: e.sort_order
        ):
            if entry.target_stage is None or entry.lead_agent is None:
                continue
            stage_lead.setdefault(entry.target_stage, entry.lead_agent)

        lead = stage_lead.get(stage)
        if lead is None:
            raise ValueError(
                f"动态资源未声明环节 {stage.value!r} 的主理"
                "（task_entries.target_stage × lead_agent），拒绝静默编派"
            )
        if lead not in agents:
            raise ValueError(
                f"主理 {lead!r} 未在 agents.json 登记，"
                "主理必须来自 AgentRegistry（动态资源）"
            )
        if agents[lead].status != AgentRuntimeStatus.ENABLED:
            raise ValueError(f"主理 {lead!r} 在动态资源里已下线（status != enabled）")

        # 2) 协理：画像仍有缺口 → 建档分析师补信息（主理本人除外）。
        assistants: list[str] = []
        analyst = AgentRole.PROFILE_ANALYST.value
        if (
            blackboard.profile is not None
            and blackboard.profile.gaps
            and lead != analyst
            and analyst in agents
        ):
            assistants.append(analyst)

        # 3) 信息侦查员：验证方向需要外部事实，按需供给、不参与结论。
        scout = AgentRole.INFO_SCOUT.value
        info_scout_required = intent == IntentType.VERIFY_DIRECTION and scout in agents

        # 4) 依据：给用户看，不带内部术语；展示名回落 agent_id 由调用方处理，
        #    这里 descriptor 一定存在（上面已校验），直接用注册名。
        descriptor = agents[lead]
        reason = f"由{descriptor.name}担任主理：{descriptor.role_summary}"

        return LeadDecision(
            lead_agent=lead,
            assistant_agents=assistants,
            info_scout_required=info_scout_required,
            reason=reason,
        )


__all__ = ["LeadPolicy", "RegistryLeadPolicy"]
