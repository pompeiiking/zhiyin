"""交接规则与"换主理必须显式告知"（FR-ORCH-003）—— 实现交付（第二波 · 后端-4）。

三条产品硬约束之一：**换主理必须显式告知**。告知不是渲染层的事，而是规则层的
判定结果——`HandoffDecision.disclosure` 为空即视为违规，前端 `DisclosureRow`
据此渲染。这条链路过去因为没有规则归属而无法回归测试。

实现口径（对着已冻结 ABC 交付）：
- `DefaultHandoffPolicy` 的判定逻辑是**纯同步、无 IO**（ABC 的 `decide` /
  `disclosure_required` 冻结为同步方法），因此"环节 → 主理"索引与展示名
  由 `from_registry()` 异步工厂在构造前从动态资源解析好传入；
  规则本体不访问 Repository，可以被单测直接驱动；
- "环节 → 主理"索引与 `RegistryLeadPolicy` 同源（task_entries 的
  `(target_stage, lead_agent)`），保证交接落点与主理选择不会各说各话；
- 展示名取自 agents.json，取不到时回落 agent_id（Port 口径允许的唯一回落，
  不静默编名字）；
- 何时告知（`disclosure_required`）：换主理、换理论、结论变化三种都算；
  首次进入（from_agent 为空）不算"换"，不告知。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import HandoffDecision
from zhiyin_business.contracts.common import Disclosure
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.enums import LoopStage


class HandoffPolicy(ABC):
    """交接判定规则。"""

    @abstractmethod
    def decide(
        self,
        *,
        blackboard: BlackboardView,
        from_stage: LoopStage,
        from_agent: str,
        to_stage: LoopStage,
        reason: str,
    ) -> HandoffDecision:
        """产出交接决策（含显式告知文案的构造依据）。"""

    @abstractmethod
    def disclosure_required(
        self,
        *,
        from_stage: LoopStage | None,
        from_agent: str | None,
        to_agent: str,
        conclusion_changed: bool = False,
        theory_changed: bool = False,
    ) -> bool:
        """是否需要显式告知。

        产品口径：换主理、换理论、结论变化三种情况都必须告知。本方法把
        "什么时候算变化"收敛到一处，避免每个调用方各判一次。
        """


class DefaultHandoffPolicy(HandoffPolicy):
    """交接判定：落点主理来自动态资源索引，告知判定三口径收敛于一处。"""

    def __init__(
        self,
        *,
        lead_index: Mapping[str, str],
        agent_names: Mapping[str, str] | None = None,
    ) -> None:
        """
        :param lead_index: 环节值（`LoopStage.value`）→ 主理 agent_id；
            来自 task_entries 的 `(target_stage, lead_agent)`，由装配方解析。
        :param agent_names: agent_id → 展示名（来自 agents.json，可选；
            缺失时告知文案回落 agent_id）。
        """
        self._lead_index = dict(lead_index)
        self._agent_names = dict(agent_names or {})

    @classmethod
    async def from_registry(cls, registry: RegistryRepository) -> "DefaultHandoffPolicy":
        """从动态资源解析构造参数（编排器 / 装配方在启动时调用一次）。"""
        entries = sorted(
            await registry.list_task_entries(), key=lambda e: e.sort_order
        )
        lead_index: dict[str, str] = {}
        for entry in entries:
            if entry.target_stage is None or entry.lead_agent is None:
                continue
            lead_index.setdefault(entry.target_stage.value, entry.lead_agent)

        agent_names = {
            agent.id: agent.name for agent in await registry.list_agents()
        }
        return cls(lead_index=lead_index, agent_names=agent_names)

    # ---------- ABC 实现 ----------

    def decide(
        self,
        *,
        blackboard: BlackboardView,
        from_stage: LoopStage,
        from_agent: str,
        to_stage: LoopStage,
        reason: str,
    ) -> HandoffDecision:
        to_agent = self._lead_index.get(to_stage.value)
        if to_agent is None:
            raise ValueError(
                f"动态资源未声明环节 {to_stage.value!r} 的主理，"
                "交接落点不确定，拒绝静默编派"
            )

        disclosure: Disclosure | None = None
        if self.disclosure_required(
            from_stage=from_stage,
            from_agent=from_agent,
            to_agent=to_agent,
        ):
            disclosure = Disclosure(
                kind="lead_change",
                text=self._disclosure_text(from_agent=from_agent, to_agent=to_agent, reason=reason),
                from_agent=from_agent,
                to_agent=to_agent,
            )

        return HandoffDecision(
            from_stage=from_stage,
            to_stage=to_stage,
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            disclosure=disclosure,
        )

    def disclosure_required(
        self,
        *,
        from_stage: LoopStage | None,
        from_agent: str | None,
        to_agent: str,
        conclusion_changed: bool = False,
        theory_changed: bool = False,
    ) -> bool:
        # 换理论 / 结论变化：无条件告知（产品硬约束）。
        if conclusion_changed or theory_changed:
            return True
        # 首次进入任务：没有"前任主理"，不算换，不告知。
        if from_agent is None:
            return False
        # 换主理：必须告知。
        return from_agent != to_agent

    # ---------- 内部 ----------

    def _display(self, agent_id: str | None) -> str:
        """展示名回落口径：注册名优先，取不到回落 agent_id（不编名字）。"""
        if agent_id is None:
            return ""
        return self._agent_names.get(agent_id, agent_id)

    def _disclosure_text(self, *, from_agent: str | None, to_agent: str, reason: str) -> str:
        if from_agent is None:
            return f"接下来由{self._display(to_agent)}为你服务：{reason}"
        return f"由{self._display(from_agent)}交接给{self._display(to_agent)}：{reason}"


__all__ = ["DefaultHandoffPolicy", "HandoffPolicy"]
