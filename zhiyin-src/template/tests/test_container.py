"""装配层测试：容器能构造、最低可用部件齐全、装配报告如实反映缺口。"""

from __future__ import annotations

import pytest

from zhiyin_boot import (
    Settings,
    assert_minimum_viable,
    build_container,
    describe_assembly,
    wire_application,
)
from zhiyin_api.runtime import WIRED


@pytest.fixture
def settings() -> Settings:
    """指向仓库内种子数据的配置，保证测试与本地演示读同一份动态资源。"""
    from pathlib import Path

    template_root = Path(__file__).resolve().parents[1]
    data_dir = template_root / "data"
    return Settings(
        env="test",
        local_data_dir=str(data_dir),
        local_registry_dir=str(data_dir / "registry"),
        local_knowledge_dir=str(data_dir / "knowledge"),
        local_object_dir=str(data_dir / "objects"),
    )


def test_container_builds(settings: Settings) -> None:
    container = build_container(settings)
    assert_minimum_viable(container)  # 不抛异常即为通过


def test_orchestration_primitives_are_wired(settings: Settings) -> None:
    container = build_container(settings)
    for name in (
        "event_bus_primitive",
        "scheduler_primitive",
        "notifier_primitive",
        "state_store",
        "agent_engine",
        "workflow_engine",
    ):
        assert getattr(container, name) is not None, f"编排原语未装配：{name}"


def test_business_service_depends_on_agent_engine(settings: Settings) -> None:
    container = build_container(settings)
    assert container.loop is not None
    # loop 必须复用容器里的同一个 AgentEngine 实例，而不是自己 new 一个。
    assert container.loop._agent is container.agent_engine


def test_scheduler_gateway_can_publish(settings: Settings) -> None:
    """调度器必须持有事件总线，否则主动事件（停滞检测）永远不触发。"""
    container = build_container(settings)
    assert container.scheduler._event_bus is container.event_bus


async def test_feature_flags_come_from_dynamic_resource(settings: Settings) -> None:
    """功能开关必须来自动态资源，而不是代码里的常量（§3.1）。"""
    container = build_container(settings)
    flags = await container.feature_flags.all()
    assert flags.get("report_full_text") is True
    assert flags.get("export") is False
    assert "mentor" in flags


def test_assembly_report_marks_first_phase_services_wired(settings: Settings) -> None:
    container = build_container(settings)
    report = describe_assembly(container)

    # 已实现的部分必须是 wired
    assert report.orchestration["agent_engine"] == WIRED
    assert report.services["loop"] == WIRED
    assert report.gateways["llm"] == WIRED

    # 第一期业务主链路和 BFF 已完整装配。
    assert report.services["orchestrator"] == WIRED
    assert report.services["facade"] == WIRED
    assert report.services["memory_service"] == WIRED
    assert report.services["asset_service"] == WIRED
    assert report.workers["impact"] == WIRED
    # M3 的向量同步能力仍会如实列入全量装配缺口。
    assert report.missing, "装配报告必须列出后续阶段缺口"
    assert not report.healthy


def test_wire_application_returns_asgi_app(settings: Settings) -> None:
    container = build_container(settings)
    app = wire_application(container)
    assert app.title.endswith("API")

    # 路由已挂载：用 openapi 断言，避免依赖 starlette 内部的路由表示形式。
    paths = set(app.openapi()["paths"])
    assert "/healthz" in paths
    # 业务路由统一挂在 /api/v1 下，前缀由 create_app 拼接（见 tests/test_api_prefix.py）
    assert "/api/v1/app/bootstrap" in paths
    assert "/api/v1/app/task/enter" in paths
