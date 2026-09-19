"""意图识别与环节判定规则（轴 B）。

对应 FR-ORCH-001：识别用户意图 → 判定当前环节；判定不确定时必须回落到
澄清追问，不允许"猜一个环节硬跳"（产品硬约束）。

与 `ports/orchestrator.py` 的关系：Orchestrator 是**调用方**，本模块是
**规则本身**。Orchestrator 负责读黑板、调规则、落库、发事件；规则只回答
"这条消息属于哪个意图""该进哪个环节"。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import IntentType, StageDecision
from zhiyin_kernel.enums import LoopStage
from zhiyin_kernel.registry import PolicyParamSet


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
    """可解释关键词规则；无法判断时返回 FREE_CHAT。

    关键词属于**规则参数**，按《AGENTS.md》§8 与 §6.4 必须来自动态资源
    `policy_params.routing.intent_keywords`，不得硬编码在 Python 里——否则调关键词
    就要发版。生产装配通过 `params_loader` 注入读取函数；未注入时使用本类内置的
    参考关键词，仅服务单元测试与本地参考实现。

    注入后**读不到参数或参数形状非法一律显式报错**，不静默回落到内置关键词：
    否则"线上改了 JSON 却没生效"会被悄悄吞掉，正是动态资源最贵的漂移。
    匹配顺序按 JSON 中的键序，先命中先生效，与文件里写的优先级一致。
    """

    IMPLEMENTATION_STATUS = "wired"

    _DEFAULT_RULES: tuple[tuple[IntentType, tuple[str, ...]], ...] = (
        (IntentType.STUCK, ("卡住", "没进展", "拖延", "做不下去")),
        (IntentType.REVIEW_DUE, ("复盘", "回顾", "好久没管")),
        (IntentType.HOW_TO_ACT, ("怎么做", "怎么行动", "计划", "不知道怎么动")),
        (IntentType.UNDECIDED, ("拿不准", "纠结", "几个方向", "选哪个")),
        (IntentType.VERIFY_DIRECTION, ("验证", "适不适合", "方向行不行", "行不行")),
        (IntentType.CONFUSED, ("迷茫", "不清楚", "适合什么", "没方向")),
    )

    def __init__(
        self,
        *,
        params_loader: Optional[Callable[[], Awaitable[Optional[PolicyParamSet]]]] = None,
    ) -> None:
        self._params_loader = params_loader

    async def classify(self, *, message: str, blackboard: BlackboardView) -> IntentType:
        normalized = message.strip().lower()
        for intent, keywords in await self._rules():
            if any(keyword in normalized for keyword in keywords):
                return intent
        return IntentType.FREE_CHAT

    async def _rules(self) -> tuple[tuple[IntentType, tuple[str, ...]], ...]:
        if self._params_loader is None:
            return self._DEFAULT_RULES
        params = await self._params_loader()
        if params is None:
            raise RuntimeError("缺少动态规则参数：routing")
        if params.status != "confirmed":
            raise RuntimeError("routing 规则参数尚未确认，不能用于意图判定")
        raw = params.value.get("intent_keywords")
        if not isinstance(raw, dict) or not raw:
            raise RuntimeError("routing.intent_keywords 必须是非空的「意图 → 关键词」映射")
        rules: list[tuple[IntentType, tuple[str, ...]]] = []
        for intent_name, keywords in raw.items():
            try:
                intent = IntentType(intent_name)
            except ValueError as exc:
                raise RuntimeError(
                    f"routing.intent_keywords 含未知意图：{intent_name}"
                ) from exc
            if (
                not isinstance(keywords, list)
                or not keywords
                or any(not isinstance(item, str) or not item.strip() for item in keywords)
            ):
                raise RuntimeError(
                    f"routing.intent_keywords[{intent_name}] 必须是非空字符串列表"
                )
            rules.append((intent, tuple(keywords)))
        return tuple(rules)


class DefaultStagePolicy(StagePolicy):
    """把确定意图映射到五环节；自由聊天按会话状态决定"留在原处"还是"追问一次"。"""

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
        if stage is not None:
            return StageDecision(stage=stage, confidence=1.0, need_clarify=False)

        # 意图无法归类，但会话已经在某个环节里：这条消息几乎一定是**在回答该环节
        # 的追问**（采集环节的"你更倾向哪类工作场景？"就是这样被回答的）。
        # 此时必须留在当前环节。否则调用方的澄清回退会把消息挡在环节之外——
        # 实测表现为每两条消息就有一条只换来一句澄清，内容从未进入环节产出，
        # 画像关键字段永远凑不满，循环卡死在①。
        current = blackboard.current_stage
        if current is not None:
            return StageDecision(stage=current, confidence=0.0, need_clarify=False)

        # 新会话且意图确实不可归类：按决策 4=A 温和追问一次；
        # 连续追问仍不确定时由 Orchestrator 回落到 fallback_stage（① 采集）。
        return StageDecision(
            stage=None,
            confidence=0.0,
            need_clarify=True,
            clarify_question="你现在更想先了解自己、验证方向，还是把目标拆成行动？",
        )


__all__ = ["DefaultStagePolicy", "IntentPolicy", "KeywordIntentPolicy", "StagePolicy"]
