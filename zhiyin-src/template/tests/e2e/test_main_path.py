"""第一期五环节主路径 e2e。

为什么现在就建这个目录
----------------------
`--check --phase=2` 的退出条件里写着"五环节主路径 e2e 通过（tests/e2e/）"，
本文件把架构文档中的七项验收口径落实成不可跳过的自动化测试。

覆盖的验收项（《第一期技术架构文档》§九）
----------------------------------------
1. 首页任务路由           → 任务入口 → 目标环节
2. 可拆可续               → 从任一环节进入，前序资产不丢
3. 动态组队               → 环节变化时主理（及协理）随之变化
4. 黑板一致               → 画像 / 行为 / 会话 / 资产可跨会话读取
5. 影响面传播             → 画像更新只重算受影响资产，版本 +1
6. 行为闭环               → 认领差距 / 选择方案 / 勾任务 / 复盘都写行为日志
7. 主动干预               → 停滞触发本地教练消息，带最小可执行动作

跑法：

    python -m pytest tests/e2e -v

前置：`python -m zhiyin_boot --check --phase=2` 的 `services` 全绿。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from zhiyin_boot import Settings, build_container

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = TEMPLATE_ROOT / "data"


def _settings() -> Settings:
    return Settings(
        env="test",
        # 这些用例刻意用本地占位模型（D1）：它产出过契约校验，正好用来验链路；
        # 没有这行显式许可，启动前置校验会拒绝装配。
        allow_placeholder_llm=True,
        local_data_dir=str(DATA_DIR),
        local_registry_dir=str(DATA_DIR / "registry"),
        local_knowledge_dir=str(DATA_DIR / "knowledge"),
        local_object_dir=str(DATA_DIR / "objects"),
    )


def _container():
    return build_container(_settings())


pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_acceptance_1_home_task_routes_to_target_stage() -> None:
    """验收项 1：首页任务路由。

    口径：`task_entries.json` 里每条任务入口声明的 `(lead_agent, target_stage)`
    都必须真的有产出契约（由 `test_shell_completeness` 守卫），
    且 `enter_task` 后会话的环节与主理等于该入口声明的值。
    """
    from zhiyin_api.dto.conversation import TaskEnterRequest
    from zhiyin_boot import wire_application

    container = _container()
    wire_application(container)

    facade = container.facade
    entries = await container.registry_service.list_task_entries()
    assert entries, "bootstrap 至少要有一个任务入口"

    routable = [entry for entry in entries if entry.target_stage is not None]
    assert routable, "至少要有一个能直接路由到环节的任务入口"

    entry = routable[0]
    view = await facade.enter_task("demo_user", TaskEnterRequest(task_code=entry.code))
    assert view.stage == entry.target_stage
    assert view.lead_agent_name, "任务入口的主理展示名必须来自动态资源"


@pytest.mark.asyncio
async def test_acceptance_2_resume_from_any_stage_keeps_prior_assets() -> None:
    """验收项 2：可拆可续。从后续环节进入时，前序资产必须仍在。"""
    from zhiyin_api.dto.conversation import TaskEnterRequest
    from zhiyin_business.contracts.common import AssetUpdateDraft
    from zhiyin_kernel.enums import AssetType

    container = _container()
    user_id = "e2e_resume"
    prior = await container.asset_service.save_version(
        user_id,
        AssetUpdateDraft(
            asset_type=AssetType.REPORT,
            depends_on_profile_keys=["career_interest"],
        ),
    )
    session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="how_to_act")
    )
    board = await container.orchestrator.read_blackboard(user_id, session.task_id)
    assert session.stage.value == "act"
    assert any(item.id == prior.id for item in board.asset_versions)


@pytest.mark.asyncio
async def test_acceptance_3_handoff_changes_lead_and_discloses() -> None:
    """验收项 3：动态组队 + 换主理必须显式告知。

    这是产品硬约束的端到端落点：`TurnResult.disclosure` 与
    `TurnResult.badge` 必须同时变化，且 disclosure 非空。
    """
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    container = _container()
    user_id = "e2e_handoff"
    session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="confused")
    )
    turn = await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=session.task_id,
            message="方向已经定了，但我不知道怎么行动",
        ),
    )
    assert turn.stage.value == "act"
    assert turn.disclosure is not None
    assert turn.disclosure["text"]
    assert turn.disclosure["from_agent"] != turn.disclosure["to_agent"]
    stored = await container.sessions.get(session.task_id)
    assert stored is not None and stored.lead_agent == turn.badge["agent_id"]


@pytest.mark.asyncio
async def test_acceptance_4_blackboard_is_shared_across_sessions() -> None:
    """验收项 4：黑板一致。第二个会话必须能读到第一个会话写入的画像与资产。"""
    from zhiyin_api.dto.conversation import TaskEnterRequest
    from zhiyin_business.contracts.common import AssetUpdateDraft
    from zhiyin_kernel.enums import AssetType

    container = _container()
    user_id = "e2e_blackboard"
    first = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="confused")
    )
    await container.profile_service.update_field(
        user_id,
        "career_interest",
        "数据工程",
        confidence=0.9,
        source="conversation",
    )
    asset = await container.asset_service.save_version(
        user_id,
        AssetUpdateDraft(
            asset_type=AssetType.REPORT,
            depends_on_profile_keys=["career_interest"],
        ),
    )
    second = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="how_to_act")
    )
    assert first.task_id != second.task_id
    board = await container.orchestrator.read_blackboard(user_id, second.task_id)
    assert board.profile is not None
    assert board.profile.fields[0].value == "数据工程"
    assert any(item.id == asset.id for item in board.asset_versions)
    assert len(board.memories) == 2


@pytest.mark.asyncio
async def test_acceptance_5_profile_update_propagates_only_affected_assets() -> None:
    """验收项 5：影响面传播。只重算受影响资产，版本 +1，未命中资产版本不变。"""
    from zhiyin_business.contracts.common import AssetUpdateDraft
    from zhiyin_kernel.enums import AssetType

    container = _container()
    user_id = "e2e_impact"
    await container.asset_service.save_version(
        user_id,
        AssetUpdateDraft(
            asset_type=AssetType.REPORT,
            depends_on_profile_keys=["skills"],
        ),
    )
    await container.asset_service.save_version(
        user_id,
        AssetUpdateDraft(
            asset_type=AssetType.DIRECTION_PLAN,
            depends_on_profile_keys=["career_interest"],
        ),
    )
    changed = await container.asset_service.propagate(user_id, ["skills"])
    assert [(item.asset_type, item.version) for item in changed] == [
        (AssetType.REPORT, 2)
    ]
    untouched = await container.asset_service.list_versions(
        user_id, AssetType.DIRECTION_PLAN
    )
    assert [item.version for item in untouched] == [1]


@pytest.mark.asyncio
async def test_acceptance_6_action_loop_writes_behavior_log() -> None:
    """验收项 6：行为闭环。认领差距 / 选择方案 / 勾任务 / 复盘都产生行为日志。"""
    from zhiyin_business.contracts.common import BehaviorEventDraft
    from zhiyin_kernel.enums import BehaviorEventType

    container = _container()
    user_id = "e2e_behavior"
    expected = {
        BehaviorEventType.GAP_CLAIM,
        BehaviorEventType.DECISION_SELECT,
        BehaviorEventType.TASK_DONE,
        BehaviorEventType.REVIEW,
    }
    for event_type in expected:
        await container.behavior_service.log(
            user_id, BehaviorEventDraft(event_type=event_type)
        )
    stored = await container.behavior_service.recent(user_id)
    assert {item.event_type for item in stored} == expected


@pytest.mark.asyncio
async def test_acceptance_7_stall_triggers_coach_message() -> None:
    """验收项 7：主动干预。停滞触发教练消息，且带最小可执行动作。"""
    from zhiyin_kernel.blackboard import BehaviorLog
    from zhiyin_kernel.enums import BehaviorEventType
    from zhiyin_orchestration import ScheduleSpec

    container = _container()
    user_id = "e2e_stall"
    task_id = "tsk_e2e_stall"
    await container.behaviors.append(
        BehaviorLog(
            id="bhv_e2e_stall",
            user_id=user_id,
            event_type=BehaviorEventType.TASK_DONE,
            occurred_at=datetime.now(timezone.utc) - timedelta(days=4),
            payload={"task_id": task_id},
        )
    )
    container.scheduler_primitive.register(
        ScheduleSpec(
            task_id="schedule_e2e_stall",
            event_type="stall_scan",
            payload={"user_id": user_id, "task_id": task_id},
        )
    )
    worker = next(item for item in container.workers if item.name == "active_event")
    assert await worker.run_once() == 1
    messages = container.notifier.list_messages(user_id)
    assert len(messages) == 1
    assert messages[0]["body"]
    assert messages[0]["action"]["type"] == "resume_review"


@pytest.mark.asyncio
async def test_acceptance_8_orchestrator_persists_full_assets_and_knowledge() -> None:
    """编排器必须保存正文，并只展示本地知识库真实命中的理论引用。"""
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest
    from zhiyin_kernel.enums import AssetType

    container = _container()
    user_id = "e2e_orchestrator_assets"

    diagnose_session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="verify_direction")
    )
    diagnose_turn = await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=diagnose_session.task_id,
            message="我想验证这个方向适不适合我",
        ),
    )
    report_versions = await container.asset_service.list_versions(
        user_id, AssetType.REPORT
    )
    report = await container.asset_service.get_report(user_id)
    assert report is not None
    assert report_versions and report.version == report_versions[-1].version
    assert report.sources

    known_theories = json.loads(
        (DATA_DIR / "knowledge" / "theory.json").read_text(encoding="utf-8")
    )
    known_ids = {item["id"] for item in known_theories["items"]}
    cited_ids = {
        item["theory_id"] for item in diagnose_turn.badge["theory_refs"]
    }
    assert cited_ids and cited_ids <= known_ids

    decide_session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="undecided")
    )
    decide_turn = await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=decide_session.task_id,
            message="几个方向拿不准，我该选哪个",
        ),
    )
    assert {
        item["theory_id"] for item in decide_turn.badge["theory_refs"]
    } <= known_ids
    directions = await container.asset_service.list_direction_plans(user_id)
    assert directions and all(item.report_id == report.id for item in directions)
    assert all(
        not gap.current_state and not gap.suggestion
        for direction in directions
        for gap in direction.gaps
    )
    selected = await container.asset_service.select_direction_plan(
        user_id, directions[0].id
    )

    act_session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="how_to_act")
    )
    await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=act_session.task_id,
            message="方向定了但不知道怎么行动",
        ),
    )
    action_plan = await container.asset_service.get_action_plan(user_id)
    assert action_plan is not None and action_plan.plan_id == selected.id
    assert action_plan.reminders_synced is False

    workspace = await container.workspace_service.build_view(user_id)
    assert workspace.report is not None
    assert workspace.direction_plans
    assert workspace.action_plan is not None

    # 报告全文必须带上③方向方案与④行动计划：它们与报告同属"活资产"。
    # 此前 API 层从未引用这两块数据，mapper 把它们丢掉了，前端只能显示空态
    # 或用编造内容顶替——DTO 里 sections 的说明却早已承诺包含它们。
    full_text = await container.facade.get_report_full_text(user_id)
    section_ids = [str(section["id"]) for section in full_text.sections]
    toc_ids = [str(item["id"]) for item in full_text.toc]
    assert toc_ids == section_ids, "目录与正文必须一致，不能出现空章节"
    assert "directions" in section_ids and "action" in section_ids

    directions_section = next(s for s in full_text.sections if s["id"] == "directions")
    plans = directions_section["content"]["plans"]
    assert [plan["id"] for plan in plans] == [plan.id for plan in directions]
    assert plans[0]["name"] == directions[0].name
    assert plans[0]["match_score"] == directions[0].match_score

    action_section = next(s for s in full_text.sections if s["id"] == "action")
    assert action_section["content"]["plan_id"] == selected.id
    assert action_section["content"]["phases"], "行动计划正文不能为空"
