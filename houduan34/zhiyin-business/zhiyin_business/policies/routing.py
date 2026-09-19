"""意图识别与环节判定规则（轴 B）—— 实现交付（第二波 · 后端-3）。

对应 FR-ORCH-001：识别用户意图 → 判定当前环节；判定不确定时必须回落到
澄清追问，不允许"猜一个环节硬跳"（产品硬约束）。

与 `ports/orchestrator.py` 的关系：Orchestrator 是**调用方**，本模块是
**规则本身**。Orchestrator 负责读黑板、调规则、落库、发事件；规则只回答
"这条消息属于哪个意图""该进哪个环节"。

实现口径（对着已冻结 ABC 交付）：
- `KeywordIntentPolicy`：规则优先——先按动态资源 `task_entries` 的任务文案做
  整句匹配，再退到关键词表；都不命中返回 FREE_CHAT（不确定就说不确定）。
  关键词表是**分类规则**（代码），任务文案与后续话术仍以动态资源为准；
- `ClarifyFirstStagePolicy`：环节判定数据驱动——意图值与任务入口 code 同名
  （`IntentType` ↔ `task_entries.code`），目标环节与主理声明全部来自动态资源，
  代码里不写死环节映射；FREE_CHAT 一律回落澄清追问；
- `policy_params.json::routing` 的 `clarify_attempts` / `fallback_stage`
  （温和追问一次、连续两次回落 ① 采集）由**编排器**持有状态执行，本规则无状态、
  不计次数。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import IntentType, StageDecision
from zhiyin_data_sdk.repositories import RegistryRepository


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


# ---------------------------------------------------------------------------
# 实现
# ---------------------------------------------------------------------------

# 关键词表：分类规则，属于代码而非文案。命中多个时取"最长关键词"（更具体者优先）。
# 兜底识别（真实模型）由编排器经 AgentEngine 完成，不在本规则内。
_INTENT_KEYWORDS: tuple[tuple[IntentType, tuple[str, ...]], ...] = (
    (
        IntentType.CONFUSED,
        (
            "不知道自己适合什么",
            "不清楚自己适合",
            "适合什么",
            "很迷茫",
            "没有方向",
            "不知道想做什么",
        ),
    ),
    (
        IntentType.VERIFY_DIRECTION,
        (
            "验证一下",
            "这个方向行不行",
            "靠不靠谱",
            "有没有戏",
            "值不值得",
            "适不适合这个方向",
        ),
    ),
    (
        IntentType.UNDECIDED,
        (
            "拿不准",
            "不知道选哪个",
            "之间纠结",
            "怎么选",
            "犹豫",
            "两个方向",
        ),
    ),
    (
        IntentType.HOW_TO_ACT,
        (
            "怎么开始",
            "怎么行动",
            "怎么做计划",
            "定下来了",
            "第一步做什么",
            "拆一下任务",
        ),
    ),
    (
        IntentType.STUCK,
        (
            "卡住了",
            "没进展",
            "坚持不下去",
            "执行不下去",
            "一直拖",
            "停滞",
        ),
    ),
    (
        IntentType.REVIEW_DUE,
        (
            "好久没",
            "该复盘",
            "回顾一下",
            "复盘一下",
            "该整理",
        ),
    ),
)

# 澄清追问话术：copies.json 暂无对应键（动态资源补键后从这里切换）。
_DEFAULT_CLARIFY_QUESTION = (
    "我想先弄清你现在最想解决的是哪件事：是还没想清方向，还是方向定了但没动手？"
)


class KeywordIntentPolicy(IntentPolicy):
    """意图识别：动态资源整句匹配 → 关键词规则 → FREE_CHAT 兜底。"""

    def __init__(self, registry: RegistryRepository | None = None) -> None:
        self._registry = registry

    async def classify(self, *, message: str, blackboard: BlackboardView) -> IntentType:
        text = (message or "").strip()
        if not text:
            return IntentType.FREE_CHAT

        # 1) 规则优先：用户消息命中任务入口文案原文（动态资源下发，即视为该意图）。
        if self._registry is not None:
            for entry in await self._registry.list_task_entries():
                label = (entry.label or "").strip()
                if label and label in text:
                    try:
                        return IntentType(entry.code)
                    except ValueError:
                        # 动态资源里出现未知 code：配置漂移，响亮失败而不是静默猜。
                        raise ValueError(
                            f"task_entries 的 code={entry.code!r} 不是合法意图值，"
                            "请同步 data/registry/task_entries.json 与 IntentType"
                        )

        # 2) 关键词规则：取"最长命中"（更具体者优先），同长按定义顺序。
        best: tuple[int, IntentType] | None = None
        for intent, keywords in _INTENT_KEYWORDS:
            for keyword in keywords:
                if keyword in text and (best is None or len(keyword) > best[0]):
                    best = (len(keyword), intent)
        if best is not None:
            return best[1]

        # 3) 不确定 → FREE_CHAT（澄清追问由 StagePolicy 决定）。
        return IntentType.FREE_CHAT


class ClarifyFirstStagePolicy(StagePolicy):
    """环节判定：意图 ↔ 任务入口同名映射（数据驱动），不确定即澄清。"""

    def __init__(self, registry: RegistryRepository) -> None:
        self._registry = registry

    async def decide(
        self,
        *,
        blackboard: BlackboardView,
        intent: IntentType,
        message: str,
    ) -> StageDecision:
        # FREE_CHAT（或无法归类）→ 不猜环节，回落澄清追问（产品硬约束）。
        if intent == IntentType.FREE_CHAT:
            return StageDecision(
                stage=None,
                confidence=0.0,
                need_clarify=True,
                clarify_question=_DEFAULT_CLARIFY_QUESTION,
            )

        # 意图值与任务入口 code 同名：目标环节以动态资源声明为准，不写死映射。
        entries = await self._registry.list_task_entries()
        entry = next((e for e in entries if e.code == intent.value), None)
        if entry is None:
            raise ValueError(
                f"task_entries 缺少 code={intent.value!r} 的入口，"
                "意图 → 环节映射来自动态资源，请先补齐 data/registry/task_entries.json"
            )
        if entry.target_stage is None:
            # 入口声明为"直接开聊"却进入了判定：仍回落澄清，不硬跳。
            return StageDecision(
                stage=None,
                confidence=0.0,
                need_clarify=True,
                clarify_question=_DEFAULT_CLARIFY_QUESTION,
            )

        return StageDecision(
            stage=entry.target_stage,
            confidence=0.9,
            need_clarify=False,
            clarify_question=None,
        )


__all__ = [
    "ClarifyFirstStagePolicy",
    "IntentPolicy",
    "KeywordIntentPolicy",
    "StagePolicy",
]
