"""装配层测试：容器能构造、最低可用部件齐全、装配报告如实反映缺口。"""

from __future__ import annotations

import json

import pytest

from zhiyin_boot import (
    Settings,
    assert_minimum_viable,
    build_container,
    describe_assembly,
    wire_application,
)
from zhiyin_api.runtime import WIRED
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalQuery


@pytest.fixture
def settings() -> Settings:
    """指向仓库内种子数据的配置，保证测试与本地演示读同一份动态资源。"""
    from pathlib import Path

    template_root = Path(__file__).resolve().parents[1]
    data_dir = template_root / "data"
    return Settings(
        env="test",
        # 刻意用本地占位模型（D1），故显式许可；否则启动前置校验拒绝装配。
        allow_placeholder_llm=True,
        local_data_dir=str(data_dir),
        local_registry_dir=str(data_dir / "registry"),
        local_knowledge_dir=str(data_dir / "knowledge"),
        local_object_dir=str(data_dir / "objects"),
    )


def test_container_builds(settings: Settings) -> None:
    container = build_container(settings)
    assert_minimum_viable(container)  # 不抛异常即为通过


def test_placeholder_llm_is_refused_without_explicit_consent(settings: Settings) -> None:
    """没接真实模型又没显式许可时，启动前置校验必须**拒绝启动**（D1）。

    这是本轮唯一的 P0 安全项：占位实现能通过产出契约校验，产出的是"结构合法但内容
    虚构"的结果。此前漏配 `ZHIYIN_USE_PAMI_LLM` 的环境会把这种产出当业务结果落库，
    而门禁、装配报告与界面三处都不报警。现在变成启动即失败。
    """
    from dataclasses import replace

    from zhiyin_boot import describe_assembly

    # 显式关掉许可：默认就是关的，这里写明是为了让用例读起来自洽
    strict = replace(settings, allow_placeholder_llm=False)
    container = build_container(strict)

    # 状态仍是 wired —— 它是完整实现，不是骨架；但必须被单独标成占位
    report = describe_assembly(container)
    assert report.gateways["llm"] == WIRED
    assert report.placeholders == ["llm"]
    # 对外提供虚构内容 → /healthz 必须降级
    assert report.serves_fabricated_content is True

    with pytest.raises(RuntimeError, match="占位实现"):
        assert_minimum_viable(container)


def test_placeholder_llm_allowed_with_explicit_consent(settings: Settings) -> None:
    """显式许可后可以启动——本地开发与 CI 靠这一行（D1）。"""
    from zhiyin_boot import describe_assembly

    assert settings.allow_placeholder_llm is True
    container = build_container(settings)
    assert_minimum_viable(container)  # 不抛异常即为通过
    # 但"允许启动"不等于"假装是真的"：占位标记照样如实上报
    assert describe_assembly(container).placeholders == ["llm"]


def test_demo_knowledge_is_reported_without_blocking_startup(
    settings: Settings, tmp_path
) -> None:
    """演示语料必须**如实上报**，但不得阻止启动（D12 选 A 的第一步）。

    两件事要同时成立，所以放在一个用例里对照着锁：

    1. **如实上报**：仓库里 `data/knowledge/*.json` 自述为 DEMO，装配报告必须把它
       标进 `demo_content`，`/healthz` 随之降级——因为相位门禁只问"search 能力位
       装没装上"，此前演示语料照样让 phase 3 判绿、healthz 判 `ok`。
    2. **不阻断启动**：内容缺失不等于服务不可用，`assert_minimum_viable` 不得因此
       抛错（这正是当初没有选"硬失败 + opt-in"那条改法的原因）。
    """
    from zhiyin_boot import describe_assembly

    container = build_container(settings)
    report = describe_assembly(container)

    # 容器里装配的 search 是 RRF 包装类，信号必须由它透传出来（否则漏报）
    assert report.gateways["search"] == WIRED
    assert report.demo_content == ["search"], "演示语料必须被如实标出"
    assert report.serves_fabricated_content is True, "/healthz 据此降级"
    # 它不是"占位实现"：实现是真的，假的是内容
    assert "search" not in report.placeholders
    # 且不阻断启动
    assert_minimum_viable(container)


def test_demo_content_is_detected_from_the_authority_store_not_the_channel(
    settings: Settings,
) -> None:
    """装配期必须能发现"权威表里是演示内容"——**哪怕检索通道不是本地通道**。

    这是切到 PAMI 之后暴露的真实回归：原来只问"本地演示通道在不在链路上"，
    换成 PAMI 后本地通道退出链路 → `demo_content` 报空、`/healthz` 报 `ok`，
    而权威表里 22 行全是 `demo=true`——系统仍在用演示内容却自称没事。

    所以检测要问**内容的权威来源**（`retrieval_document`）。本用例用一个假的
    authority 替身来锁这个口径（真实 store 的查询由 `test_phase3_rag` 覆盖）。
    """
    container = build_container(settings)
    # 把检索通道换成一个**不自述演示**的替身（模拟"已切到 PAMI，本地通道退出链路"）
    container.search = type("NonDemoChannel", (), {})()

    class DemoAuthority:
        def demo_namespaces(self) -> list[str]:
            return ["theory", "occupation"]

    container.extra["retrieval_authority"] = DemoAuthority()
    report = describe_assembly(container)
    assert report.demo_content == ["search"], "通道不报，也要从权威表查出来"
    assert report.demo_namespaces == ["theory", "occupation"]
    assert report.serves_fabricated_content is True, "/healthz 必须降级"
    # 仍然不阻断启动：内容缺失不等于服务不可用（D12 选 A）
    assert_minimum_viable(container)


def test_demo_detection_failure_does_not_claim_clean(settings: Settings) -> None:
    """权威表查不出来时**不得**当作"内容是真的"。

    "不知道"与"干净"是两件事；把前者当后者，正是 D12 要根治的那类谎报。
    这里也不中断启动，而是显式记成未知并让 `/healthz` 降级。
    """
    container = build_container(settings)

    class BrokenAuthority:
        def demo_namespaces(self) -> list[str]:
            raise RuntimeError("数据库连不上")

    container.extra["retrieval_authority"] = BrokenAuthority()
    report = describe_assembly(container)
    assert report.demo_content_unknown is True
    assert report.serves_fabricated_content is True
    assert_minimum_viable(container)


def test_no_authority_means_no_false_positive(settings: Settings) -> None:
    """没有权威表（如纯本地/无 MySQL）时**不得**凭空报"演示内容"。"""
    container = build_container(settings)
    container.extra.pop("retrieval_authority", None)
    report = describe_assembly(container)
    assert report.demo_content_unknown is False
    # 本地通道自述演示（仓库语料），所以这里仍应是 search——但来源是通道自述
    assert report.demo_content == ["search"]
    assert report.demo_namespaces == [], "没有权威表就不该编出 namespace 范围"


def test_real_corpus_is_not_flagged_as_demo(settings: Settings, tmp_path) -> None:
    """反向用例：语料自述不是演示数据时**不得**误报（避免"到处都标红"而失效）。"""
    from dataclasses import replace

    from zhiyin_boot import describe_assembly

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "theory.json").write_text(
        json.dumps(
            {
                "_note": "真实采集并评审通过的公共知识条目。",
                "items": [
                    {
                        "id": "t-1",
                        "namespace": "theory",
                        "title": "某理论",
                        "summary": "真实来源",
                        "status": "enabled",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    real = replace(settings, local_knowledge_dir=str(knowledge))
    report = describe_assembly(build_container(real))
    # 只看"演示内容"这一维：本 fixture 的 llm 仍是占位实现，所以合并后的
    # serves_fabricated_content 本来就会是 True，用它判断会掩盖这里的真实意图。
    assert report.demo_content == []
    assert report.placeholders == ["llm"], "占位维度不受影响"


def test_demo_detection_follows_the_data_not_the_path(settings: Settings, tmp_path) -> None:
    """判定依据是**语料自己的声明**，不是目录名/环境名。

    为什么专门锁这条：按路径或 `env` 猜"这是不是演示内容"看起来更省事，但换目录、
    改环境名时会静默失效——那时系统又会重新"不知道内容是假的"，而这正是 D12 要
    根治的事。这里把同一份演示语料放到任意目录，标记必须照样生效。
    """
    from dataclasses import replace

    from zhiyin_infrastructure.local.knowledge import LocalSearchGateway

    elsewhere = tmp_path / "some" / "other" / "dir"
    elsewhere.mkdir(parents=True)
    (elsewhere / "whatever.json").write_text(
        json.dumps(
            {"_note": "DEMO 语料，仅用于本地链路验证", "items": []}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    gateway = LocalSearchGateway(str(elsewhere))
    assert gateway.serves_demo_content is True

    report = describe_assembly(
        build_container(replace(settings, local_knowledge_dir=str(elsewhere)))
    )
    assert report.demo_content == ["search"]


@pytest.mark.asyncio
async def test_demo_corpus_evidence_is_flagged_for_citation_check(
    settings: Settings,
) -> None:
    """演示语料的命中必须能被**逐条识别**出来（D12 第二步的前置）。

    装配报告只能说明"这条通道的内容是演示的"；要让引用核对拒绝演示证据，命中本身
    就得带标记。这里锁住标记的存在与取值，避免第二步做了个假动作。
    """
    container = build_container(settings)
    hits = await container.search.search(
        RetrievalQuery(
            query="霍兰德", namespace=RetrievalNamespace.THEORY, top_k=3
        )
    )
    assert hits, "演示语料里应有可召回条目"
    assert all(hit.metadata.get("demo") is True for hit in hits), (
        f"演示命中缺少 demo 标记：{[hit.metadata for hit in hits]}"
    )


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
    assert report.services["profile_service"] == WIRED
    assert report.services["behavior_service"] == WIRED
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
