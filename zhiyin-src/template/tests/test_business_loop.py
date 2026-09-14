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


async def test_advance_keeps_inherited_assets(coordinator, registry) -> None:
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

    advanced = await coord.advance(context, LoopStage.DIAGNOSE)
    assert advanced.stage is LoopStage.DIAGNOSE
    assert advanced.inherited_assets == context.inherited_assets, "推进环节不得丢前序资产"


async def test_advance_uses_explicit_lead_when_given(coordinator) -> None:
    """交接主理由调用方（Orchestrator + policies）决定，本类不得倒过来猜。

    兜底口径（任务入口默认主理）与目标环节无关，因此显式传入必须优先。
    """
    context = await coordinator.start(_entry(LoopStage.COLLECT, "profile_analyst"))
    advanced = await coordinator.advance(
        context, LoopStage.REVIEW, lead_agent="companion_coach"
    )
    assert advanced.stage is LoopStage.REVIEW
    assert advanced.lead_agent == "companion_coach"


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
    spec = await registry.get_output_contract("oc_collect")
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
