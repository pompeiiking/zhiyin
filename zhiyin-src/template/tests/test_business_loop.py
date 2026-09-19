"""五环节 Loop 参考实现测试。

锁住三件事：
1. business 层真的通过编排层 AgentEngine 拿产出（依赖不是摆设）；
2. 产出契约校验生效，非法产出不会进入业务层；
3. 可拆可续：任意环节进入、前序资产继承、续接不重建会话。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zhiyin_orchestration import ContractAgentEngine
from zhiyin_kernel.enums import LoopStage
from zhiyin_data_sdk.gateways.ai import LLMGateway, LLMMessage, LLMResult

from zhiyin_business.services import (
    STAGE_OUTPUT_CONTRACTS,
    STAGE_SEQUENCE,
    AgentDrivenLoopCoordinator,
    next_stage_after,
)
from zhiyin_business.services.loop import build_stage_instruction

from zhiyin_infrastructure.local.repository import (
    InMemoryTaskSessionRepository,
    LocalJsonRegistryRepository,
)
from zhiyin_infrastructure.local.llm import LocalOrMockLLM

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def registry() -> LocalJsonRegistryRepository:
    return LocalJsonRegistryRepository(str(DATA_DIR / "registry"))


@pytest.fixture
def sessions() -> InMemoryTaskSessionRepository:
    return InMemoryTaskSessionRepository()


@pytest.fixture
def coordinator(sessions, registry) -> AgentDrivenLoopCoordinator:
    # LocalOrMockLLM 会按产出契约的 JSON Schema 合成合法结果，
    # 因此这条链路能真正跑到契约校验通过的那一步。
    engine = ContractAgentEngine(LocalOrMockLLM())
    return AgentDrivenLoopCoordinator(engine, sessions, registry)


def _entry(stage: LoopStage, lead: str, task_code: str = "confused"):
    from zhiyin_business.ports.loop import LoopEntry

    return LoopEntry(user_id="u1", task_code=task_code, stage=stage, lead_agent=lead)


# --------------------------------------------------------------------------
# 契约与阶段顺序
# --------------------------------------------------------------------------


def test_every_stage_has_an_output_contract() -> None:
    for stage in LoopStage:
        assert stage in STAGE_OUTPUT_CONTRACTS, f"环节 {stage} 缺少产出契约"


def test_stage_sequence_follows_prd() -> None:
    assert STAGE_SEQUENCE == (
        LoopStage.COLLECT,
        LoopStage.DIAGNOSE,
        LoopStage.DECIDE,
        LoopStage.ACT,
        LoopStage.REVIEW,
    )
    assert next_stage_after(LoopStage.COLLECT) is LoopStage.DIAGNOSE
    assert next_stage_after(LoopStage.REVIEW) is None


# --------------------------------------------------------------------------
# 从任意环节进入
# --------------------------------------------------------------------------


async def test_run_collect_stage(coordinator) -> None:
    context = await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    result = await coordinator.run_stage(context, "我还不太清楚自己适合什么")

    assert result.stage is LoopStage.COLLECT
    # 主理展示名来自动态资源，不是硬编码
    assert result.badge.name == "建档分析师"
    # 每轮必须以后续引导收尾（FR-ORCH-007）
    assert result.guide.kind in {"question", "options", "task", "reminder"}
    assert result.output["guide"]["kind"] == result.guide.kind


async def test_run_diagnose_stage_produces_conclusion(coordinator) -> None:
    context = await coordinator.start(
        _entry(LoopStage.DIAGNOSE, "career_advisor", "verify_direction")
    )
    result = await coordinator.run_stage(context, "想验证某方向行不行")

    # ② 诊断的结论取自 verdict.summary（见 default_conclusion_builder）
    assert result.messages, "② 应产出最短结论"
    assert result.messages[0].agent_id == "career_advisor"
    assert result.badge.name == "职业顾问"


async def test_all_stages_run(coordinator) -> None:
    """五个环节都要能跑通并产出契约合法的结果。"""
    leads = {
        LoopStage.COLLECT: "profile_analyst",
        LoopStage.DIAGNOSE: "career_advisor",
        LoopStage.DECIDE: "career_advisor",
        LoopStage.ACT: "path_planner",
        LoopStage.REVIEW: "companion_coach",
    }
    for stage, lead in leads.items():
        context = await coordinator.start(_entry(stage, lead, f"task_{stage.value}"))
        result = await coordinator.run_stage(context, "继续")
        assert "degraded" not in result.output, f"{stage} 产出被降级：{result.output}"


async def test_success_path_carries_model_degraded(coordinator) -> None:
    """成功路径也必须带上模型级降级标记（D1）。

    回归点：`LocalOrMockLLM` 每次都返回 `LLMResult.degraded=True`，但产出**通过了**
    契约校验，所以它既不走降级分支、也不被任何门禁拦下。此前 `result.degraded`
    只在失败路径被塞进 `output`，成功路径直接丢弃——于是占位产出会被当真实资产落库，
    而"看起来一切正常"。现在 `LoopResult.model_degraded` 在成功路径上也如实为 True。
    """
    context = await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    result = await coordinator.run_stage(context, "我想做结构设计")

    # 契约校验通过：不是降级产出
    assert "degraded" not in result.output
    # 但模型自述降级，必须如实透出，不能被丢掉
    assert result.model_degraded is True


# --------------------------------------------------------------------------
# 可拆可续
# --------------------------------------------------------------------------


async def test_start_reuses_active_session(coordinator, sessions) -> None:
    first = await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    second = await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))

    assert first.session.id == second.session.id, "同一任务的进行中会话必须被续接而不是重建"
    assert len(await sessions.list_by_user("u1")) == 1


async def test_start_from_arbitrary_stage_switches_stage(coordinator) -> None:
    await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    later = await coordinator.start(_entry(LoopStage.ACT, "path_planner"))

    assert later.stage is LoopStage.ACT
    assert later.lead_agent == "path_planner"


async def test_resume_keeps_persisted_stage(coordinator) -> None:
    context = await coordinator.start(
        _entry(LoopStage.DECIDE, "career_advisor", "undecided")
    )
    resumed = await coordinator.resume("u1", context.session.id)

    assert resumed.stage is LoopStage.DECIDE
    assert resumed.session.id == context.session.id


async def test_resume_rejects_wrong_user(coordinator) -> None:
    context = await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    with pytest.raises(PermissionError):
        await coordinator.resume("someone-else", context.session.id)


async def test_inherited_assets_come_from_the_blackboard(coordinator, registry) -> None:
    """"前序资产自动继承"发生在**读黑板**这一步，且续接时同样成立。

    本用例原来叫 `test_advance_keeps_inherited_assets`，靠 `advance()` 来断言
    "推进环节不得丢前序资产"。`advance` 已于 2026-09-19 删除（待决问题 D3），
    所以断言移到仍然存在的两个入口：首次进入 `start()` 与会话续接 `resume()`——
    它们才是真正负责"从黑板取继承资产"的地方。阶段变更本身现在只走
    `Orchestrator.handoff`（守卫见 `tests/test_orchestrator_second_wave.py`）。
    """
    from datetime import datetime, timezone

    from zhiyin_kernel.blackboard import AssetVersion
    from zhiyin_kernel.enums import AssetType

    from zhiyin_business.ports.blackboard import BlackboardView

    saved = AssetVersion(
        id="av_1",
        user_id="u1",
        asset_type=AssetType.REPORT,
        version=1,
        created_at=datetime.now(timezone.utc),
        depends_on_profile_keys=["major"],
    )

    async def loader(user_id: str, task_id: str | None) -> BlackboardView:
        return BlackboardView(user_id=user_id, task_id=task_id, asset_versions=[saved])

    coord = AgentDrivenLoopCoordinator(
        ContractAgentEngine(LocalOrMockLLM()),
        InMemoryTaskSessionRepository(),
        registry,
        blackboard_loader=loader,
    )

    context = await coord.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    # 进入 ① 时已带上 ② 的资产 → 证明"前序资产自动继承"发生在读黑板这一步
    assert [asset.asset_type for asset in context.inherited_assets] == [AssetType.REPORT]

    # 续接走的也必须是同一份黑板：从任意环节进入都不重建上下文
    resumed = await coord.resume("u1", context.session.id)
    assert [asset.asset_type for asset in resumed.inherited_assets] == [AssetType.REPORT]


# --------------------------------------------------------------------------
# 降级
# --------------------------------------------------------------------------


class _BrokenLLM(LLMGateway):
    """返回结构缺失的产出，模拟模型不守契约。"""

    async def chat(self, messages: list[LLMMessage], *, json_schema=None, temperature=0.2, timeout_s=60.0):
        return LLMResult(text="乱答", structured={"unexpected": True}, model="broken")


async def test_invalid_output_is_degraded_not_injected(sessions, registry) -> None:
    """非法产出不得进入业务层（R-ORC-002），但也不能中断核心调用链（§6.2）。"""
    coord = AgentDrivenLoopCoordinator(
        ContractAgentEngine(_BrokenLLM()),
        sessions,
        registry,
        degraded_guide_text="（降级文案，接动态资源后从 app_copy 读取）",
    )
    context = await coord.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    result = await coord.run_stage(context, "hi")

    assert result.output["degraded"] is True
    assert result.output["errors"]
    # 仍须给出一轮可展示的结果，而不是抛异常
    assert result.guide.text
    assert result.badge.agent_id == "profile_analyst"


async def test_contract_schema_comes_from_registry_when_present(sessions, registry) -> None:
    """产出契约优先取动态资源；种子数据里留空则应回落到模型生成的 Schema。"""
    # 查找键是 (agent_id, stage)，不是契约 id
    spec = await registry.get_output_contract("profile_analyst", LoopStage.COLLECT)
    assert spec is not None
    assert spec.model_ref.endswith("CollectOutput")
    assert spec.json_schema == {}

    coord = AgentDrivenLoopCoordinator(
        ContractAgentEngine(LocalOrMockLLM()), sessions, registry
    )
    context = await coord.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    schema = await coord._output_schema(context)
    assert schema.get("type") == "object"
    assert "guide" in schema.get("properties", {})


async def test_dimension_tag_is_a_closed_enum_not_free_text(sessions, registry) -> None:
    """15 维的 `tag` 必须是闭合枚举，且这个约束要真的进到模型的 Schema 里。

    背景：`tag` 原为自由字符串，实测模型产出 11 种措辞（已确认/待验证/未定义/缺失/
    待确认/部分匹配/无依据/严重不足/未知/低/未建立）。它对前端有两个后果：
    既无法上色（没有稳定取值集合），又把"证据够不够"与"这一维好不好"混在一句里。
    收敛成 `DimensionEvidenceLevel` 四档后，本测试锁三件事：
    1. 非法自由串被拒（否则收紧无效）；
    2. Schema 里以 enum 形式暴露（否则模型不受约束，只是后端事后报错）；
    3. 四档取值稳定（改枚举就是改契约，必须让本测试红）。
    """
    from pydantic import ValidationError

    from zhiyin_kernel.assets import ReportDimensionItem
    from zhiyin_kernel.enums import DimensionEvidenceLevel

    assert [level.value for level in DimensionEvidenceLevel] == [
        "confirmed",
        "partial",
        "pending",
        "missing",
    ]

    for level in DimensionEvidenceLevel:
        item = ReportDimensionItem(
            index=1, name="职业兴趣", tag=level, conclusion="结论", evidence="依据"
        )
        # 落到 DTO/JSON 里必须是字符串值，前端才能直接比对
        assert item.model_dump(mode="json")["tag"] == level.value

    for bad in ("已确认", "优势", "confirmed "):
        with pytest.raises(ValidationError):
            ReportDimensionItem(
                index=1, name="职业兴趣", tag=bad, conclusion="结论", evidence="依据"
            )

    # 模型实际收到的是模型自省生成的 Schema（output_contracts.json 的 json_schema 为空）
    spec = await registry.get_output_contract("career_advisor", LoopStage.DIAGNOSE)
    assert spec is not None and spec.json_schema == {}
    coord = AgentDrivenLoopCoordinator(ContractAgentEngine(LocalOrMockLLM()), sessions, registry)
    context = await coord.start(_entry(LoopStage.DIAGNOSE, "career_advisor"))
    schema = await coord._output_schema(context)
    tag_schema = schema["$defs"]["ReportDimensionItem"]["properties"]["tag"]
    level_def = schema["$defs"]["DimensionEvidenceLevel"]
    assert tag_schema["$ref"].endswith("DimensionEvidenceLevel")
    assert level_def["enum"] == ["confirmed", "partial", "pending", "missing"]


async def test_contract_lookup_is_per_stage_not_per_agent(sessions, registry) -> None:
    """同一个智能体在不同环节必须取到不同的契约。

    职业顾问同时负责 ②诊断 与 ③决策。此前契约按"智能体唯一的
    output_contract_id"查，②③ 会取到同一条(②)，`oc_decide` 成为无人引用的孤儿。
    这条测试把 (agent_id, stage) 这个口径钉住。
    """
    diagnose = await registry.get_output_contract("career_advisor", LoopStage.DIAGNOSE)
    decide = await registry.get_output_contract("career_advisor", LoopStage.DECIDE)

    assert diagnose is not None and decide is not None
    assert diagnose.id != decide.id, "② 与 ③ 必须是两条不同的契约"
    assert diagnose.stage is LoopStage.DIAGNOSE
    assert decide.stage is LoopStage.DECIDE

    # 取不到的 (agent_id, stage) 组合返回 None，不抛异常（由调用方回落）
    assert await registry.get_output_contract("profile_analyst", LoopStage.REVIEW) is None


# --------------------------------------------------------------------------
# 环节指令组装（五环节没有提示词时，真实模型只能自造画像字段名）
# --------------------------------------------------------------------------


def test_stage_instruction_carries_role_and_boundary() -> None:
    text = build_stage_instruction(
        LoopStage.DIAGNOSE,
        agent_name="职业顾问",
        role_summary="画像与目标要求对齐",
        not_to_do=["不替用户执行"],
    )
    assert "职业顾问" in text
    assert "画像与目标要求对齐" in text
    assert "不替用户执行" in text
    # 只输出 JSON 的硬要求必须随每条指令下发
    assert "JSON" in text


def test_collect_instruction_lists_key_fields_and_thresholds() -> None:
    """关键字段清单与阈值由调用方从 policy_params 传入，指令里必须原样出现。"""
    key_fields = ["career_interest", "ability_strength", "value_anchor"]
    text = build_stage_instruction(
        LoopStage.COLLECT,
        agent_name="建档分析师",
        key_fields=key_fields,
        coverage_threshold=0.8,
        confidence_threshold=0.7,
        gap_confidence_floor=0.6,
    )
    for key in key_fields:
        assert key in text, f"指令必须列出关键字段 {key}"
    assert "0.8" in text and "0.7" in text and "0.6" in text
    assert "field_updates" in text and "remaining_gaps" in text


def test_collect_instruction_does_not_invent_key_fields() -> None:
    """没有传入关键字段时不得凭空编造——否则就是绕过动态资源口径。"""
    text = build_stage_instruction(LoopStage.COLLECT, agent_name="建档分析师")
    for leaked in ("career_interest", "ability_strength", "value_anchor"):
        assert leaked not in text


def test_non_collect_instruction_has_no_profile_field_block() -> None:
    text = build_stage_instruction(LoopStage.ACT, agent_name="路径规划师")
    assert "field_updates" not in text
    assert "remaining_gaps" not in text


def test_key_fields_from_params_requires_confirmed_params() -> None:
    from zhiyin_business.policies.profile import (
        PROFILE_COLLECTION_POLICY,
        key_fields_from_params,
    )
    from zhiyin_kernel.registry import PolicyParamSet

    good = PolicyParamSet(
        code=PROFILE_COLLECTION_POLICY,
        value={"key_fields": ["a", "b"]},
        status="confirmed",
    )
    assert key_fields_from_params(good) == ["a", "b"]

    for bad in (
        PolicyParamSet(code=PROFILE_COLLECTION_POLICY, value={"key_fields": []}, status="confirmed"),
        PolicyParamSet(code=PROFILE_COLLECTION_POLICY, value={"key_fields": ["a", "a"]}, status="confirmed"),
        PolicyParamSet(code=PROFILE_COLLECTION_POLICY, value={"key_fields": "a"}, status="confirmed"),
        PolicyParamSet(code=PROFILE_COLLECTION_POLICY, value={"key_fields": ["a"]}, status="draft"),
        PolicyParamSet(code="other", value={"key_fields": ["a"]}, status="confirmed"),
    ):
        with pytest.raises(ValueError):
            key_fields_from_params(bad)

