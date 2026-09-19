"""后端-2 第一阶段数据全链路 E2E。

只走容器公开 Service 与事件总线，不直接操作 Repository 制造验收结果。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from zhiyin_boot import Settings, build_container
from zhiyin_business.events import PROFILE_FIELD_UPDATED, ProfileFieldUpdatedPayload
from zhiyin_kernel.assets import CalendarNode, Report, Swot, Verdict
from zhiyin_kernel.enums import AssetType, LoopStage
from zhiyin_orchestration import DomainEvent

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = TEMPLATE_ROOT / "data"

pytestmark = pytest.mark.e2e


def _container(tmp_path: Path):
    return build_container(
        Settings(
            env="test",
            # 刻意用本地占位模型（D1），故显式许可；否则启动前置校验拒绝装配。
            allow_placeholder_llm=True,
            local_data_dir=str(DATA_DIR),
            local_registry_dir=str(DATA_DIR / "registry"),
            local_knowledge_dir=str(DATA_DIR / "knowledge"),
            local_object_dir=str(tmp_path / "objects"),
            redis_url="",
        )
    )


async def test_profile_event_propagates_content_and_workspace_reads_it(
    tmp_path: Path,
) -> None:
    container = _container(tmp_path)
    user_id = "e2e-data-owner"

    await container.memory_service.upsert(
        user_id,
        "task-data",
        loop_stage=LoopStage.DIAGNOSE,
        lead_agent="career_advisor",
        summary_delta="已确认计算机专业，正在验证数据方向",
    )
    await container.asset_service.save_report(
        user_id,
        Report(
            id="report-data-owner",
            user_id=user_id,
            version=0,
            generated_at=datetime.now(timezone.utc),
            verdict=Verdict(title="方向诊断", summary="优先验证数据工程方向"),
            swot=Swot(strength=["编程基础"], weakness=["项目证据不足"]),
            sources=["DEMO 本地公共知识"],
        ),
        depends_on_profile_keys=["major", "skills"],
    )

    await container.profile_service.update_field(
        user_id,
        "major",
        "计算机类",
        confidence=1.0,
        source="conversation",
        evidence=["用户本轮明确确认"],
    )
    impact = next(worker for worker in container.workers if worker.name == "impact")
    assert await impact.run_once() == 1
    assert await impact.run_once() == 0

    versions = await container.asset_service.list_versions(user_id, AssetType.REPORT)
    assert [item.version for item in versions] == [1, 2]
    assert "major" in (versions[-1].diff_from_previous or "")
    assert (await container.asset_service.get_report(user_id)).version == 2

    workspace = await container.workspace_service.build_view(user_id)
    assert workspace.profile is not None
    assert workspace.report is not None and workspace.report.version == 2
    assert workspace.panels[1].version == 2
    assert workspace.dependencies[0].to_asset == "report"

    full_text = await container.function_service.get_report_full_text(user_id, 2)
    assert full_text["available"] is True
    assert full_text["report"]["verdict"]["summary"] == "优先验证数据工程方向"

    resumed = await container.memory_service.get(user_id, "task-data")
    assert resumed is not None
    assert resumed.loop_stage is LoopStage.DIAGNOSE
    assert "数据方向" in resumed.summary


async def test_duplicate_profile_event_and_user_data_are_isolated(tmp_path: Path) -> None:
    container = _container(tmp_path)
    user_id = "e2e-idempotent"
    other_user = "e2e-other"
    await container.asset_service.save_report(
        user_id,
        Report(
            id="report-idempotent",
            user_id=user_id,
            version=0,
            generated_at=datetime.now(timezone.utc),
            verdict=Verdict(title="诊断", summary="待验证"),
            swot=Swot(),
        ),
        depends_on_profile_keys=["skills"],
    )
    impact = next(worker for worker in container.workers if worker.name == "impact")
    payload = ProfileFieldUpdatedPayload(
        user_id=user_id,
        field_key="skills",
        confidence=0.9,
        source="conversation",
        profile_version=2,
        updated_at=datetime.now(timezone.utc),
    ).model_dump(mode="json")
    event = DomainEvent(
        event_id="evt-data-duplicate",
        event_type=PROFILE_FIELD_UPDATED,
        occurred_at=datetime.now(timezone.utc),
        payload=payload,
        idempotency_key="profile:e2e-idempotent:skills:2",
    )
    await container.event_bus_primitive.publish(event)
    await container.event_bus_primitive.publish(event)
    assert await impact.run_once() == 1
    assert len(await container.asset_service.list_versions(user_id, AssetType.REPORT)) == 2
    assert await container.asset_service.list_versions(other_user, AssetType.REPORT) == []
    assert await container.function_service.get_report_full_text(other_user) == {
        "available": False,
        "report": None,
        "message": "尚未生成诊断报告",
    }

    node = await container.function_service.write_calendar_node(
        user_id,
        CalendarNode(node_id="autumn-apply", title="秋招网申截止", source="planner"),
    )
    assert node.user_id == user_id
    assert len(await container.function_service.list_calendar_nodes(user_id)) == 1
    assert await container.function_service.list_calendar_nodes(other_user) == []
