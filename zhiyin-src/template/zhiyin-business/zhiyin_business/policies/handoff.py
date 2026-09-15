"""交接规则与"换主理必须显式告知"（FR-ORCH-003）。

三条产品硬约束之一：**换主理必须显式告知**。告知不是渲染层的事，而是规则层
的判定结果——`HandoffDecision.disclosure` 为空即视为违规，前端 `DisclosureRow`
据此渲染。这条链路过去因为没有规则归属而无法回归测试。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import HandoffDecision
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
        to_agent: str | None = None,
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
    """根据环节/主理变化生成强制显式告知。"""

    IMPLEMENTATION_STATUS = "wired"

    def decide(
        self,
        *,
        blackboard: BlackboardView,
        from_stage: LoopStage,
        from_agent: str,
        to_stage: LoopStage,
        reason: str,
        to_agent: str | None = None,
    ) -> HandoffDecision:
        target_agent = to_agent or from_agent
        disclosure = None
        if self.disclosure_required(
            from_stage=from_stage,
            from_agent=from_agent,
            to_agent=target_agent,
        ):
            from zhiyin_business.contracts.common import Disclosure

            disclosure = Disclosure(
                kind="lead_change",
                text=f"接下来进入{to_stage.value}环节，由新的主理继续帮助你：{reason}",
                from_agent=from_agent,
                to_agent=target_agent,
            )
        return HandoffDecision(
            from_stage=from_stage,
            to_stage=to_stage,
            from_agent=from_agent,
            to_agent=target_agent,
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
        return (
            from_agent is not None and from_agent != to_agent
        ) or conclusion_changed or theory_changed


__all__ = ["DefaultHandoffPolicy", "HandoffPolicy"]
