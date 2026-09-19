"""意图识别与环节判定规则测试（`policies/routing.py`）。

锁住两件事：
1. 会话已经在某个环节里时，无法归类的消息必须**留在当前环节**——
   否则每两条消息就有一条被澄清吞掉，用户的话永远进不了环节产出；
2. 关键词是**规则参数**，必须来自 `policy_params.routing.intent_keywords`，
   读不到或形状非法时显式报错，不静默回落到内置关键词。
"""

from __future__ import annotations

import pytest

from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import IntentType
from zhiyin_business.policies.routing import (
    DefaultStagePolicy,
    KeywordIntentPolicy,
)
from zhiyin_kernel.enums import LoopStage
from zhiyin_kernel.registry import PolicyParamSet


def _blackboard(stage: LoopStage | None) -> BlackboardView:
    return BlackboardView(user_id="u1", current_stage=stage)


# --------------------------------------------------------------------------
# 环节判定
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_known_intents_map_to_their_stage() -> None:
    policy = DefaultStagePolicy()
    for intent, stage in (
        (IntentType.CONFUSED, LoopStage.COLLECT),
        (IntentType.VERIFY_DIRECTION, LoopStage.DIAGNOSE),
        (IntentType.UNDECIDED, LoopStage.DECIDE),
        (IntentType.HOW_TO_ACT, LoopStage.ACT),
        (IntentType.STUCK, LoopStage.REVIEW),
        (IntentType.REVIEW_DUE, LoopStage.REVIEW),
    ):
        decision = await policy.decide(
            blackboard=_blackboard(LoopStage.COLLECT), intent=intent, message="x"
        )
        assert decision.stage is stage
        assert decision.need_clarify is False


@pytest.mark.asyncio
async def test_free_chat_inside_a_stage_stays_in_that_stage() -> None:
    """回归：采集环节的追问就是这样被回答的，不能被澄清拦掉。

    此前的行为是无论会话在哪一环节都返回 need_clarify，调用方的澄清回退
    每两条消息吃掉一条，内容从未进入环节产出，画像关键字段永远凑不满。
    """
    policy = DefaultStagePolicy()
    decision = await policy.decide(
        blackboard=_blackboard(LoopStage.COLLECT),
        intent=IntentType.FREE_CHAT,
        message="我熟练使用 AutoCAD、PKPM、YJK，做过两个课程设计。",
    )
    assert decision.stage is LoopStage.COLLECT
    assert decision.need_clarify is False


@pytest.mark.asyncio
async def test_free_chat_without_a_session_clarifies_once() -> None:
    """新会话且意图确实不可归类时，仍按决策 4=A 温和追问。"""
    policy = DefaultStagePolicy()
    decision = await policy.decide(
        blackboard=_blackboard(None), intent=IntentType.FREE_CHAT, message="你好"
    )
    assert decision.stage is None
    assert decision.need_clarify is True
    assert decision.clarify_question


# --------------------------------------------------------------------------
# 关键词规则参数
# --------------------------------------------------------------------------


def _routing_params(value: dict, *, status: str = "confirmed") -> PolicyParamSet:
    return PolicyParamSet(code="routing", status=status, value=value)


@pytest.mark.asyncio
async def test_keywords_come_from_dynamic_params() -> None:
    params = _routing_params(
        {"clarify_attempts": 1, "fallback_stage": "collect",
         "intent_keywords": {"review_due": ["自定义词"]}}
    )

    async def loader() -> PolicyParamSet:
        return params

    policy = KeywordIntentPolicy(params_loader=loader)
    assert await policy.classify(message="我用了自定义词", blackboard=_blackboard(None)) is IntentType.REVIEW_DUE
    # 内置参考词不再生效：动态资源是唯一事实来源
    assert await policy.classify(message="我想复盘", blackboard=_blackboard(None)) is IntentType.FREE_CHAT


@pytest.mark.asyncio
async def test_builtin_keywords_only_without_a_loader() -> None:
    policy = KeywordIntentPolicy()
    assert await policy.classify(message="我卡住了", blackboard=_blackboard(None)) is IntentType.STUCK
    assert await policy.classify(message="随便聊聊", blackboard=_blackboard(None)) is IntentType.FREE_CHAT


@pytest.mark.asyncio
async def test_missing_or_invalid_keyword_params_fail_explicitly() -> None:
    """注入 loader 后参数缺失/形状非法必须报错，不得静默回落。"""

    async def none_loader():
        return None

    with pytest.raises(RuntimeError, match="routing"):
        await KeywordIntentPolicy(params_loader=none_loader).classify(
            message="x", blackboard=_blackboard(None)
        )

    for bad_value in (
        {"clarify_attempts": 1},  # 没有 intent_keywords
        {"intent_keywords": {}},
        {"intent_keywords": {"not_an_intent": ["a"]}},
        {"intent_keywords": {"stuck": []}},
        {"intent_keywords": {"stuck": "卡住"}},
    ):

        async def bad_loader(value=bad_value):
            return _routing_params(value)

        with pytest.raises(RuntimeError):
            await KeywordIntentPolicy(params_loader=bad_loader).classify(
                message="x", blackboard=_blackboard(None)
            )

    async def draft_loader():
        return _routing_params({"intent_keywords": {"stuck": ["卡住"]}}, status="draft")

    with pytest.raises(RuntimeError, match="尚未确认"):
        await KeywordIntentPolicy(params_loader=draft_loader).classify(
            message="x", blackboard=_blackboard(None)
        )


def test_shipped_policy_params_declare_intent_keywords() -> None:
    """仓内动态资源必须真的带上关键词，否则全新环境会直接显式失败。"""
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[1] / "data" / "registry"
    raw = json.loads((data_dir / "policy_params.json").read_text(encoding="utf-8"))
    routing = next(item for item in raw["items"] if item["code"] == "routing")
    keywords = routing["value"]["intent_keywords"]
    assert keywords, "routing.intent_keywords 不能为空"
    for intent, words in keywords.items():
        assert IntentType(intent) is not None
        assert words and all(isinstance(word, str) and word.strip() for word in words)


# --------------------------------------------------------------------------
# D5：用户主动要求进入②诊断
# --------------------------------------------------------------------------

_EXPLICIT_ADVANCE = (
    "我想开始诊断",
    "现在进入诊断吧",
    "帮我做诊断",
    "我的档案够了",
    "可以进入下一环节了",
)
"""注意这里**故意不含**"进入下一步"：`下一步` 本身就是 `how_to_act` 的关键词，
而 `how_to_act` 的键序在 `verify_direction` 之前——"下一步"在两处都讲得通，
按键序归 `how_to_act` 是合理的。想要表达"推进环节"要用无歧义的说法。"""


@pytest.mark.asyncio
@pytest.mark.parametrize("message", _EXPLICIT_ADVANCE)
async def test_explicit_advance_request_reaches_diagnose(message: str) -> None:
    """用户主动说"开始诊断"必须真的进②，而不是被留在①。

    这条守卫的是**规则参数**（`policy_params.routing.intent_keywords`）：显式推进
    不需要新端点，只需让这些表达落进已映射到 `DIAGNOSE` 的 `verify_direction`。
    参数化到具体句子是刻意的——`KeywordIntentPolicy` 按 JSON 键序**先命中先生效**，
    若新词与 `confused` / `how_to_act` 等更靠前的组撞车，本测试会直接红。
    """
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[1] / "data" / "registry"
    raw = json.loads((data_dir / "policy_params.json").read_text(encoding="utf-8"))
    routing = next(
        item for item in raw["items"] if item["code"] == "routing"
    )["value"]

    async def loader() -> PolicyParamSet:
        return _routing_params(routing)

    intent = await KeywordIntentPolicy(params_loader=loader).classify(
        message=message, blackboard=_blackboard(LoopStage.COLLECT)
    )
    assert intent is IntentType.VERIFY_DIRECTION, f"{message!r} 被判成了 {intent}"

    decision = await DefaultStagePolicy().decide(
        blackboard=_blackboard(LoopStage.COLLECT), intent=intent, message=message
    )
    assert decision.stage is LoopStage.DIAGNOSE
    assert decision.need_clarify is False


async def _shipped_intent(message: str) -> IntentType:
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[1] / "data" / "registry"
    raw = json.loads((data_dir / "policy_params.json").read_text(encoding="utf-8"))
    routing = next(item for item in raw["items"] if item["code"] == "routing")["value"]

    async def loader() -> PolicyParamSet:
        return _routing_params(routing)

    return await KeywordIntentPolicy(params_loader=loader).classify(
        message=message, blackboard=_blackboard(LoopStage.COLLECT)
    )


@pytest.mark.asyncio
async def test_narrative_mentioning_review_word_does_not_enter_review() -> None:
    """回归：叙述里出现「复盘 / 回顾」不能被当成"该复盘了"。

    实测缺陷：用户在 ① 采集被追问时回答「帮社团做过活动数据复盘」，
    旧关键词表里的裸词「复盘」命中 → 环节被判成 ⑤ 复盘，会话被从 ① 拽走；
    ⑤ 产出又判定"需要再入环"，于是二次交接到 ②。用户看到的告知是
    「接下来进入② 诊断匹配环节…：⑤ 复盘判定需要再入环」——`stage` 与告知
    自相矛盾。匹配是整句子串包含，裸名词必然误伤，故关键词只能是**意图短语**。
    """
    for narrative in (
        "我平时喜欢整理数据、做表格分析，帮社团做过活动数据复盘，觉得挺有成就感。",
        "这段实习让我学会了怎么系统地回顾一次项目的问题。",
    ):
        assert (
            await _shipped_intent(narrative) is IntentType.FREE_CHAT
        ), f"叙述被误判：{narrative}"

    # 反过来，"表达复盘意图"的说法仍然必须进 ⑤。
    assert await _shipped_intent("我这周的进展该复盘了") is IntentType.REVIEW_DUE
