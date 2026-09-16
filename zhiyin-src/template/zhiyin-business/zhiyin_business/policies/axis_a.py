"""轴 A 职业发展阶段推断规则。

规则层只根据黑板中的可观测事实给出确定结论；证据不足时返回 ``None``，
由 Orchestrator 使用通用 AgentEngine 做模型兜底。这样规则不会重新流回
``services/orchestrator.py``，也不会让策略层依赖具体模型实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_kernel.enums import AxisAStage, BehaviorEventType, PathFocus


class AxisAInferencePolicy(ABC):
    """根据黑板事实推断轴 A；无法可靠判断时返回 ``None``。"""

    @abstractmethod
    def infer(
        self,
        *,
        blackboard: BlackboardView,
        path_focus: PathFocus | None,
    ) -> AxisAStage | None:
        """执行规则优先的阶段推断。"""


class RuleFirstAxisAInferencePolicy(AxisAInferencePolicy):
    """第一期可解释规则：关键行为优先，其次读取画像事实。"""

    IMPLEMENTATION_STATUS = "wired"

    _KEY_BEHAVIORS = frozenset(
        {
            BehaviorEventType.TASK_STALL,
            BehaviorEventType.DECISION_RESELECT,
            BehaviorEventType.REVIEW,
            BehaviorEventType.TASK_DONE,
        }
    )

    def infer(
        self,
        *,
        blackboard: BlackboardView,
        path_focus: PathFocus | None,
    ) -> AxisAStage | None:
        del path_focus  # 路径焦点保留给后续细化规则；第一期不据此猜阶段。

        latest_signal = next(
            (
                item.event_type
                for item in blackboard.recent_behaviors
                if item.event_type in self._KEY_BEHAVIORS
            ),
            None,
        )
        if latest_signal in {
            BehaviorEventType.TASK_STALL,
            BehaviorEventType.DECISION_RESELECT,
        }:
            return AxisAStage.REPOSITION
        if latest_signal is BehaviorEventType.REVIEW:
            return AxisAStage.ADAPT
        if latest_signal is BehaviorEventType.TASK_DONE:
            return AxisAStage.SPRINT_ACTION

        profile = blackboard.profile
        if profile is None or not profile.fields:
            return AxisAStage.EXPLORE_SELF
        if any(
            field.key == "target_direction" and _has_value(field.value) for field in profile.fields
        ):
            return AxisAStage.VERIFY_DIRECTION
        return None


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


__all__ = ["AxisAInferencePolicy", "RuleFirstAxisAInferencePolicy"]
