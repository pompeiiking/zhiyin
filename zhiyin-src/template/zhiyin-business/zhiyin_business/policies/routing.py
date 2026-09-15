"""意图识别与环节判定规则（轴 B）。

对应 FR-ORCH-001：识别用户意图 → 判定当前环节；判定不确定时必须回落到
澄清追问，不允许"猜一个环节硬跳"（产品硬约束）。

与 `ports/orchestrator.py` 的关系：Orchestrator 是**调用方**，本模块是
**规则本身**。Orchestrator 负责读黑板、调规则、落库、发事件；规则只回答
"这条消息属于哪个意图""该进哪个环节"。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import IntentType, StageDecision
from zhiyin_kernel.enums import LoopStage


class IntentPolicy(ABC):
    """把一条用户消息归类为意图（FR-HOME-001 / FR-HOME-003）。"""

    @abstractmethod
    async def classify(self, *, message: str, blackboard: BlackboardView) -> IntentType:
        """识别意图。规则优先 + 关键词/模型兜底；不确定时返回 FREE_CHAT。"""


class StagePolicy(ABC):
    """由意图与黑板状态判定目标环节。"""

    @abstractmethod
    async def decide(
        self,
        *,
        blackboard: BlackboardView,
        intent: IntentType,
        message: str,
    ) -> StageDecision:
        """判定环节。

        契约要求：
        - 判定不确定时置 `need_clarify=True` 并给出 `clarify_question`，
          由调用方渲染澄清追问，而不是推进环节；
        - `confidence` 必须如实反映把握程度，调用方按阈值决定是否追问。
        """


class KeywordIntentPolicy(IntentPolicy):
    """第一期可解释关键词规则；无法判断时返回 FREE_CHAT。"""

    IMPLEMENTATION_STATUS = "wired"

    _RULES = (
        (IntentType.STUCK, ("卡住", "没进展", "拖延", "做不下去")),
        (IntentType.REVIEW_DUE, ("复盘", "回顾", "好久没管")),
        (IntentType.HOW_TO_ACT, ("怎么做", "怎么行动", "计划", "不知道怎么动")),
        (IntentType.UNDECIDED, ("拿不准", "纠结", "几个方向", "选哪个")),
        (IntentType.VERIFY_DIRECTION, ("验证", "适不适合", "方向行不行")),
        (IntentType.CONFUSED, ("迷茫", "不清楚", "适合什么", "没方向")),
    )

    async def classify(self, *, message: str, blackboard: BlackboardView) -> IntentType:
        normalized = message.strip().lower()
        for intent, keywords in self._RULES:
            if any(keyword in normalized for keyword in keywords):
                return intent
        return IntentType.FREE_CHAT


class DefaultStagePolicy(StagePolicy):
    """把确定意图映射到五环节；自由聊天温和澄清。"""

    IMPLEMENTATION_STATUS = "wired"

    _STAGES = {
        IntentType.CONFUSED: LoopStage.COLLECT,
        IntentType.VERIFY_DIRECTION: LoopStage.DIAGNOSE,
        IntentType.UNDECIDED: LoopStage.DECIDE,
        IntentType.HOW_TO_ACT: LoopStage.ACT,
        IntentType.STUCK: LoopStage.REVIEW,
        IntentType.REVIEW_DUE: LoopStage.REVIEW,
    }

    async def decide(
        self,
        *,
        blackboard: BlackboardView,
        intent: IntentType,
        message: str,
    ) -> StageDecision:
        stage = self._STAGES.get(intent)
        if stage is None:
            return StageDecision(
                stage=None,
                confidence=0.0,
                need_clarify=True,
                clarify_question="你现在更想先了解自己、验证方向，还是把目标拆成行动？",
            )
        return StageDecision(stage=stage, confidence=1.0, need_clarify=False)


__all__ = ["DefaultStagePolicy", "IntentPolicy", "KeywordIntentPolicy", "StagePolicy"]
