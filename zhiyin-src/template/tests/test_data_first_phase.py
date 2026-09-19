"""数据能力全链路第一期业务验收。"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from zhiyin_business.contracts.common import AssetUpdateDraft
from zhiyin_business.events import (
    ASSET_VERSION_CHANGED,
    PROFILE_FIELD_UPDATED,
    ProfileFieldUpdatedPayload,
)
from zhiyin_business.policies import DependencyImpactPolicy
from zhiyin_business.services import (
    DefaultAssetService,
    DefaultConversationMemoryService,
    DefaultFunctionService,
    DefaultWorkspaceService,
)
from zhiyin_business.workers import ImpactPropagationWorker
from zhiyin_infrastructure.crawl import (
    KnowledgeIngestionPipeline,
    KnowledgeSource,
    KnowledgeSourceAdapter,
    ReviewDecision,
)
from zhiyin_infrastructure.local.cache import InMemoryCache
from zhiyin_infrastructure.local.feature_flag import LocalFeatureFlagStore
from zhiyin_infrastructure.local.messaging import InMemoryEventBus
from zhiyin_infrastructure.local.knowledge import LocalSearchGateway
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalQuery
from zhiyin_infrastructure.local.object_store import LocalFileStore
from zhiyin_infrastructure.local.repository import (
    InMemoryAssetRepository,
    InMemoryConversationMemoryRepository,
    InMemoryTaskSessionRepository,
    LocalJsonRegistryRepository,
)
from zhiyin_kernel.assets import CalendarNode, Report, Swot, Verdict
from zhiyin_kernel.blackboard import BehaviorLog
from zhiyin_kernel.enums import AssetType, BehaviorEventType, LoopStage
from zhiyin_orchestration import DomainEvent, GatewayEventBus

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _event_bus() -> GatewayEventBus:
    return GatewayEventBus(InMemoryEventBus())


async def test_memory_create_append_and_isolate() -> None:
    service = DefaultConversationMemoryService(InMemoryConversationMemoryRepository())

    first = await service.upsert(
        "u1",
        "task-1",
        loop_stage=LoopStage.COLLECT,
        lead_agent="profile_analyst",
        summary_delta="已确认专业",
    )
    second = await service.upsert(
        "u1",
        "task-1",
        loop_stage=LoopStage.DIAGNOSE,
        lead_agent="career_advisor",
        summary_delta="开始诊断",
    )
    unchanged = await service.upsert(
        "u1",
        "task-1",
        loop_stage=LoopStage.DIAGNOSE,
        lead_agent="career_advisor",
        summary_delta="   ",
    )
    await service.upsert(
        "u2",
        "task-1",
        loop_stage=LoopStage.COLLECT,
        lead_agent="profile_analyst",
        summary_delta="另一个用户",
    )

    assert first.id == second.id
    assert second.summary == "已确认专业\n开始诊断"
    assert unchanged.summary == second.summary
    assert len(await service.list_by_user("u1")) == 1
    assert (await service.get("u2", "task-1")).summary == "另一个用户"


async def test_memory_deduplicates_retries_and_bounds_long_term_summary() -> None:
    service = DefaultConversationMemoryService(
        InMemoryConversationMemoryRepository(), max_summary_chars=12
    )
    for fragment in ("已确认专业", "已确认专业", "开始方向诊断", "准备行动"):
        memory = await service.upsert(
            "u1",
            "task-1",
            loop_stage=LoopStage.DIAGNOSE,
            lead_agent="career_advisor",
            summary_delta=fragment,
        )
    assert memory.summary == "开始方向诊断\n准备行动"
    assert memory.summary.count("已确认专业") == 0
    assert len(memory.summary) <= 12


async def test_memory_concurrent_appends_do_not_lose_fragments() -> None:
    service = DefaultConversationMemoryService(InMemoryConversationMemoryRepository())
    await asyncio.gather(
        *[
            service.upsert(
                "u1",
                "task-1",
                loop_stage=LoopStage.COLLECT,
                lead_agent="profile_analyst",
                summary_delta=f"并发摘要-{index}",
            )
            for index in range(20)
        ]
    )
    memory = await service.get("u1", "task-1")
    assert memory is not None
    assert set(memory.summary.splitlines()) == {
        f"并发摘要-{index}" for index in range(20)
    }


async def test_asset_versions_events_and_affected_scope() -> None:
    repo = InMemoryAssetRepository()
    bus = _event_bus()
    received: list[DomainEvent] = []
    bus.subscribe(ASSET_VERSION_CHANGED, received.append)
    service = DefaultAssetService(repo, bus, DependencyImpactPolicy())

    report = await service.save_version(
        "u1",
        AssetUpdateDraft(asset_type=AssetType.REPORT, depends_on_profile_keys=["major", "major"]),
    )
    await service.save_version(
        "u1",
        AssetUpdateDraft(
            asset_type=AssetType.ACTION_PLAN,
            depends_on_profile_keys=["target_city"],
        ),
    )
    propagated = await service.propagate("u1", ["major"])

    assert report.version == 1 and report.diff_from_previous is None
    assert report.depends_on_profile_keys == ["major"]
    assert [item.asset_type for item in propagated] == [AssetType.REPORT]
    assert propagated[0].version == 2
    assert "major" in propagated[0].diff_from_previous
    assert len(await service.list_versions("u1", AssetType.ACTION_PLAN)) == 1
    assert [event.payload["to_version"] for event in received] == [1, 1, 2]


async def test_asset_content_snapshot_tracks_version_and_concurrent_writes() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(repo, _event_bus(), DependencyImpactPolicy())
    first = await service.save_report(
        "u1",
        Report(
            id="report-u1",
            user_id="u1",
            version=99,
            generated_at=_now(),
            verdict=Verdict(title="方向诊断", summary="适合数据方向"),
            swot=Swot(),
        ),
        depends_on_profile_keys=["major"],
    )
    changed = await service.propagate("u1", ["major"])
    assert first.version == 1
    assert changed[0].version == 2
    assert (await service.get_report("u1", 1)).version == 1
    assert (await service.get_report("u1")).version == 2

    concurrent = await asyncio.gather(
        *[
            service.save_version(
                "u2", AssetUpdateDraft(asset_type=AssetType.ACTION_PLAN)
            )
            for _ in range(20)
        ]
    )
    assert sorted(item.version for item in concurrent) == list(range(1, 21))


async def test_asset_does_not_publish_when_save_fails() -> None:
    class BrokenAssets(InMemoryAssetRepository):
        async def save_version(self, version):
            raise RuntimeError("storage unavailable")

    bus = _event_bus()
    received: list[DomainEvent] = []
    bus.subscribe(ASSET_VERSION_CHANGED, received.append)
    service = DefaultAssetService(BrokenAssets(), bus, DependencyImpactPolicy())

    with pytest.raises(RuntimeError):
        await service.save_version(
            "u1", AssetUpdateDraft(asset_type=AssetType.REPORT)
        )
    assert received == []


async def test_asset_snapshot_failure_rolls_back_version_content_and_event() -> None:
    class BrokenSnapshotAssets(InMemoryAssetRepository):
        async def save_snapshot(self, version, **kwargs):
            raise RuntimeError("snapshot unavailable")

    repo = BrokenSnapshotAssets()
    bus = _event_bus()
    received: list[DomainEvent] = []
    bus.subscribe(ASSET_VERSION_CHANGED, received.append)
    service = DefaultAssetService(repo, bus, DependencyImpactPolicy())
    with pytest.raises(RuntimeError, match="snapshot unavailable"):
        await service.save_report(
            "u1",
            Report(
                id="report-u1",
                user_id="u1",
                version=1,
                generated_at=_now(),
                verdict=Verdict(title="测试", summary="测试"),
                swot=Swot(),
            ),
        )
    assert await repo.list_versions("u1", AssetType.REPORT) == []
    assert await repo.get_report("u1") is None
    assert received == []


async def test_impact_worker_is_semantically_idempotent() -> None:
    repo = InMemoryAssetRepository()
    bus = _event_bus()
    service = DefaultAssetService(repo, bus, DependencyImpactPolicy())
    await service.save_version(
        "u1",
        AssetUpdateDraft(asset_type=AssetType.REPORT, depends_on_profile_keys=["major"]),
    )
    worker = ImpactPropagationWorker(service, bus)
    payload = ProfileFieldUpdatedPayload(
        user_id="u1",
        field_key="major",
        confidence=0.9,
        source="conversation",
        profile_version=2,
        updated_at=_now(),
    ).model_dump(mode="json")
    for index in range(2):
        await bus.publish(
            DomainEvent(
                event_id=f"evt-{index}",
                event_type=PROFILE_FIELD_UPDATED,
                occurred_at=_now(),
                payload=payload,
            )
        )

    assert await worker.run_once() == 1
    assert await worker.run_once() == 0
    assert len(await service.list_versions("u1", AssetType.REPORT)) == 2


async def test_impact_worker_keeps_failed_event_for_retry() -> None:
    class FailOnceAssets(InMemoryAssetRepository):
        fail_next = False

        async def save_snapshot(self, version, **kwargs):
            if self.fail_next:
                self.fail_next = False
                raise RuntimeError("temporary storage failure")
            return await super().save_snapshot(version, **kwargs)

    repo = FailOnceAssets()
    bus = _event_bus()
    service = DefaultAssetService(repo, bus, DependencyImpactPolicy())
    await service.save_version(
        "u1",
        AssetUpdateDraft(
            asset_type=AssetType.REPORT, depends_on_profile_keys=["major"]
        ),
    )
    worker = ImpactPropagationWorker(service, bus)
    repo.fail_next = True
    await bus.publish(
        DomainEvent(
            event_id="evt-retry",
            event_type=PROFILE_FIELD_UPDATED,
            occurred_at=_now(),
            payload=ProfileFieldUpdatedPayload(
                user_id="u1",
                field_key="major",
                confidence=0.9,
                source="conversation",
                profile_version=2,
                updated_at=_now(),
            ).model_dump(mode="json"),
            idempotency_key="profile:u1:major:2",
        )
    )
    with pytest.raises(RuntimeError):
        await worker.run_once()
    assert await worker.run_once() == 1
    assert [
        item.version
        for item in await service.list_versions("u1", AssetType.REPORT)
    ] == [1, 2]


async def test_impact_worker_idempotency_survives_worker_restart() -> None:
    repo = InMemoryAssetRepository()
    cache = InMemoryCache()
    service = DefaultAssetService(repo, _event_bus(), DependencyImpactPolicy())
    await service.save_version(
        "u1",
        AssetUpdateDraft(
            asset_type=AssetType.REPORT, depends_on_profile_keys=["major"]
        ),
    )
    payload = ProfileFieldUpdatedPayload(
        user_id="u1",
        field_key="major",
        confidence=0.9,
        source="conversation",
        profile_version=2,
        updated_at=_now(),
    ).model_dump(mode="json")

    first_bus = _event_bus()
    first_worker = ImpactPropagationWorker(service, first_bus, cache)
    await first_bus.publish(
        DomainEvent(
            event_id="evt-first",
            event_type=PROFILE_FIELD_UPDATED,
            occurred_at=_now(),
            payload=payload,
            idempotency_key="profile:u1:major:2",
        )
    )
    assert await first_worker.run_once() == 1

    restarted_bus = _event_bus()
    restarted_worker = ImpactPropagationWorker(service, restarted_bus, cache)
    await restarted_bus.publish(
        DomainEvent(
            event_id="evt-redelivery",
            event_type=PROFILE_FIELD_UPDATED,
            occurred_at=_now(),
            payload=payload,
            idempotency_key="profile:u1:major:2",
        )
    )
    assert await restarted_worker.run_once() == 0
    assert len(await service.list_versions("u1", AssetType.REPORT)) == 2


class _EmptyProfiles:
    async def get(self, user_id: str):
        raise RuntimeError("profile temporarily unavailable")


class _Behaviors:
    def __init__(self, logs: list[BehaviorLog] | None = None) -> None:
        self.logs = logs or []

    async def recent(self, user_id: str, *, event_types=None, limit: int = 50):
        items = [item for item in self.logs if item.user_id == user_id]
        if event_types:
            items = [item for item in items if item.event_type in event_types]
        return items[:limit]


async def test_agent_capability_pool_is_resolved_server_side() -> None:
    """能力池必须由业务读侧解析好：负责环节反推自产出契约，理论包翻成中文名（D9）。

    此前前端把五位智能体的完整定义硬编码在 `stores/agents.ts`，与
    `data/registry/agents.json` 靠人工同步——违反《AGENTS.md》§8，漂移了也没有守卫。
    现在由 `RegistryService.list_agent_capabilities()` 一次解析：
    - `stages` 用**已有的** `get_output_contract(agent_id, stage)` 逐环节探测得出，
      不给 Repository 加 `list_output_contracts`、也不在 agents.json 里加冗余字段；
    - `theories` 把理论卡 id 翻成中文名（否则前端要么硬编码映射，要么显示 `parsons_self`）。
    """
    from zhiyin_business.services.registry import DefaultRegistryService

    registry = LocalJsonRegistryRepository(str(DATA_DIR / "registry"))
    service = DefaultRegistryService(registry, LocalFeatureFlagStore(str(DATA_DIR / "registry")))
    capabilities = await service.list_agent_capabilities()

    assert [item.agent.id for item in capabilities] == [
        "profile_analyst",
        "career_advisor",
        "path_planner",
        "companion_coach",
        "info_scout",
    ]
    stages = {item.agent.id: [stage.value for stage in item.stages] for item in capabilities}
    # 负责环节由产出契约反推：职业顾问同时管②诊断与③决策
    assert stages["career_advisor"] == ["diagnose", "decide"]
    assert stages["profile_analyst"] == ["collect"]
    assert stages["path_planner"] == ["act"]
    assert stages["companion_coach"] == ["review"]
    # 信息侦查员不绑定环节：如实为空，界面按"全环节按需调用"呈现
    assert stages["info_scout"] == []

    # 理论中文名已解析（不是 id）
    analyst = next(item for item in capabilities if item.agent.id == "profile_analyst")
    assert analyst.theories, "建档分析师必须带上理论卡"
    assert all(card.name and card.name != card.id for card in analyst.theories)


async def test_workspace_available_blocks_is_derived_from_feature_flags() -> None:
    """可用功能块必须由功能开关派生，不得在 Python 里再抄一份清单（D8）。

    此前 `available_blocks` 是写死的字面量，把 `export` / `mentor`（注册表里
    `enabled: false`）和 `demo` 一并列成 "available"：既违反《AGENTS.md》§8
    （功能开关不得硬编码），语义也错——`available` 应当就是 `enabled`。
    """
    import json

    flags_path = DATA_DIR / "registry" / "feature_flags.json"
    declared = {
        item["code"]: bool(item["enabled"])
        for item in json.loads(flags_path.read_text(encoding="utf-8"))["items"]
    }
    expected = sorted(code for code, enabled in declared.items() if enabled)

    workspace = DefaultWorkspaceService(
        profiles=_EmptyProfiles(),
        assets=DefaultAssetService(
            InMemoryAssetRepository(), _event_bus(), DependencyImpactPolicy()
        ),
        memories=DefaultConversationMemoryService(InMemoryConversationMemoryRepository()),
        behaviors=_Behaviors(),
        registry=LocalJsonRegistryRepository(str(DATA_DIR / "registry")),
        features=LocalFeatureFlagStore(str(DATA_DIR / "registry")),
        sessions=InMemoryTaskSessionRepository(),
    )

    view = await workspace.build_view("u1")
    assert view.available_blocks == expected
    # 关掉的开关绝不能出现在"可用"里；`demo` 这个演示能力位已下架
    assert "export" not in view.available_blocks  # enabled=false
    assert "mentor" not in view.available_blocks  # enabled=false
    assert "demo" not in view.available_blocks


async def test_workspace_partial_failure_still_returns_five_panels() -> None:
    memories = DefaultConversationMemoryService(InMemoryConversationMemoryRepository())
    assets = DefaultAssetService(InMemoryAssetRepository(), _event_bus(), DependencyImpactPolicy())
    workspace = DefaultWorkspaceService(
        profiles=_EmptyProfiles(),
        assets=assets,
        memories=memories,
        behaviors=_Behaviors(),
        registry=LocalJsonRegistryRepository(str(DATA_DIR / "registry")),
        features=LocalFeatureFlagStore(str(DATA_DIR / "registry")),
        sessions=InMemoryTaskSessionRepository(),
    )

    view = await workspace.build_view("u1")
    assert view.profile is None
    # 空画像没有口径问题：两项派生指标都是 0，不去读参数
    assert view.profile_coverage == 0.0
    assert view.profile_overall_confidence == 0.0
    assert [panel.stage for panel in view.panels] == list(LoopStage)
    assert "尚未建立画像" in view.panels[0].evaluation


async def test_function_calendar_achievement_track_and_export(tmp_path: Path) -> None:
    logs = [
        BehaviorLog(
            id="b1",
            user_id="u1",
            event_type=BehaviorEventType.TASK_DONE,
            occurred_at=_now(),
            payload={"task_id": "t1"},
        )
    ]
    object_store = LocalFileStore(str(tmp_path / "objects"))
    assets = DefaultAssetService(
        InMemoryAssetRepository(), _event_bus(), DependencyImpactPolicy()
    )
    behaviors = _Behaviors(logs)
    service = DefaultFunctionService(
        assets=assets,
        behaviors=behaviors,
        object_store=object_store,
    )

    node = await service.write_calendar_node(
        "u1", CalendarNode(node_id="n1", title="投递截止", source="planner")
    )
    assert node.user_id == "u1"
    assert len(await service.list_calendar_nodes("u1")) == 1
    assert await service.list_calendar_nodes("u2") == []
    restarted = DefaultFunctionService(
        assets=assets,
        behaviors=behaviors,
        object_store=LocalFileStore(str(tmp_path / "objects")),
    )
    assert [item.node_id for item in await restarted.list_calendar_nodes("u1")] == [
        "n1"
    ]
    with pytest.raises(PermissionError):
        await service.write_calendar_node(
            "u1", CalendarNode(node_id="n2", user_id="u2", title="越权")
        )

    achievements = await service.list_achievements("u1")
    assert [item.badge_key for item in achievements] == ["first_task_done"]
    assert all(item.driven_by_behavior_log_only for item in achievements)
    assert [item.type for item in await service.list_track_events("u1")] == [
        "milestone_done"
    ]
    export = await service.export_asset("u1", "report", "pdf")
    assert export.available is False and export.object_key is None
    assert (await service.get_demo_script()).read_only is True


async def test_calendar_concurrent_writes_across_service_instances(tmp_path: Path) -> None:
    root = tmp_path / "objects"
    assets = DefaultAssetService(
        InMemoryAssetRepository(), _event_bus(), DependencyImpactPolicy()
    )
    first = DefaultFunctionService(
        assets=assets,
        behaviors=_Behaviors(),
        object_store=LocalFileStore(str(root)),
    )
    second = DefaultFunctionService(
        assets=assets,
        behaviors=_Behaviors(),
        object_store=LocalFileStore(str(root)),
    )
    await asyncio.gather(
        *[
            (first if index % 2 == 0 else second).write_calendar_node(
                "u1", CalendarNode(node_id=f"n-{index}", title=f"节点 {index}")
            )
            for index in range(20)
        ]
    )
    assert len(await first.list_calendar_nodes("u1")) == 20


async def test_compliant_ingestion_is_idempotent_traceable_and_removable(
    tmp_path: Path,
) -> None:
    class RawStore:
        def __init__(self) -> None:
            self.writes: list[tuple[str, str, object, int]] = []

        async def set_json(self, entity, identifier, value, *, ttl_s):
            self.writes.append((entity, identifier, value, ttl_s))

    refreshed: list[str] = []
    raw_store = RawStore()
    pipeline = KnowledgeIngestionPipeline(
        tmp_path,
        refreshed.append,
        raw_store=raw_store,
        raw_ttl_s=900,
        reviewer=lambda source, item: ReviewDecision(
            status="approved", reviewer="reviewer-1", reason="字段与来源已核验"
        ),
    )
    source = KnowledgeSource(
        source_id="src-open",
        name="开放数据",
        source_url="https://example.test/open-data",
        namespace="occupation",
        acquisition="open_data",
        access_basis="官方开放数据许可",
        allowed=True,
        allowed_scope="公开职业名称与简介",
        owner="data-owner",
        refresh_interval="daily",
        removal_method="source_id",
        retention="30 days",
        status="enabled",
    )

    async def fetcher(_: KnowledgeSource):
        return {"items": [{"id": "occ-1", "title": "数据分析师", "summary": "分析数据"}]}

    first = await pipeline.run(source, fetcher, trace_id="trace-e2e-ingestion")
    second = await pipeline.run(source, fetcher)
    stored = __import__("json").loads(
        (tmp_path / "occupation.json").read_text(encoding="utf-8")
    )["items"][0]

    assert (first.stored, second.stored, second.unchanged) == (1, 0, 1)
    assert stored["source_id"] == source.source_id
    assert stored["source_item_id"] == "occ-1"
    assert stored["trace_id"] == second.trace_id
    assert stored["batch_id"] == second.batch_id
    assert stored["review_status"] == "approved"
    assert stored["version"] == 1 and len(stored["content_hash"]) == 64
    assert first.trace_id == "trace-e2e-ingestion"
    assert len(raw_store.writes) == 2
    assert all(write[0] == "raw" and write[3] == 900 for write in raw_store.writes)
    assert pipeline.disable_source("occupation", source.source_id) == 1
    assert refreshed == ["occupation", "occupation"]


async def test_ingestion_rejects_unapproved_source(tmp_path: Path) -> None:
    pipeline = KnowledgeIngestionPipeline(tmp_path)
    source = KnowledgeSource(
        source_id="src-pending",
        name="待确认站点",
        source_url="https://example.test",
        namespace="jd",
        acquisition="allowed_page",
        access_basis="待确认",
        allowed=False,
        allowed_scope="待确认",
        owner="data-owner",
        refresh_interval="disabled",
        removal_method="source_id",
        retention="none",
        status="pending_review",
    )
    with pytest.raises(PermissionError):
        await pipeline.run(source, lambda _: [])


async def test_ingestion_isolates_sources_and_rejects_namespace_traversal(
    tmp_path: Path,
) -> None:
    pipeline = KnowledgeIngestionPipeline(
        tmp_path,
        reviewer=lambda source, item: ReviewDecision(
            status="approved", reviewer="reviewer-1", reason="测试审核通过"
        ),
    )

    def source(source_id: str, namespace: str = "occupation") -> KnowledgeSource:
        return KnowledgeSource(
            source_id=source_id,
            name=source_id,
            source_url="https://example.test/open",
            namespace=namespace,
            acquisition="open_data",
            access_basis="官方开放数据许可",
            allowed=True,
            allowed_scope="公开职业字段",
            owner="data-owner",
            refresh_interval="daily",
            removal_method="source_id",
            retention="30 days",
            status="enabled",
        )

    async def same_id(_: KnowledgeSource):
        return {"items": [{"id": "same", "title": "同名站内记录"}]}

    await pipeline.run(source("source-a"), same_id)
    await pipeline.run(source("source-b"), same_id)
    payload = __import__("json").loads(
        (tmp_path / "occupation.json").read_text(encoding="utf-8")
    )
    assert {item["id"] for item in payload["items"]} == {
        "source-a:same",
        "source-b:same",
    }
    assert pipeline.disable_item("occupation", "source-a", "same", version=1) == 1
    assert pipeline.remove_source("occupation", "source-b") == 1

    with pytest.raises(ValueError):
        await pipeline.run(source("bad", "../outside"), same_id)


async def test_ingestion_requires_review_and_parses_html_file(tmp_path: Path) -> None:
    source = KnowledgeSource(
        source_id="source-html",
        name="开放 HTML 卡片",
        source_url="https://example.test/open",
        namespace="occupation",
        acquisition="allowed_page",
        access_basis="页面条款明确允许复用公开职业卡片",
        allowed=True,
        allowed_scope="data-id、data-title 与公开摘要",
        owner="data-owner",
        refresh_interval="daily",
        removal_method="source_id",
        retention="30 days",
        status="enabled",
    )
    html = tmp_path / "items.html"
    html.write_text(
        '<article data-id="occ-1" data-title="数据分析师">分析公开数据</article>',
        encoding="utf-8",
    )
    pending = KnowledgeIngestionPipeline(tmp_path / "pending")
    pending_report = await pending.run(source, lambda _: html)
    pending_item = json.loads(
        (tmp_path / "pending" / "occupation.json").read_text(encoding="utf-8")
    )["items"][0]
    assert pending_report.pending_review == 1
    assert pending_item["status"] == "pending_review"
    assert not await LocalSearchGateway(str(tmp_path / "pending")).search(
        RetrievalQuery(query="数据分析师", namespace=RetrievalNamespace.OCCUPATION)
    )

    refreshed: list[str] = []
    approved = KnowledgeIngestionPipeline(
        tmp_path / "pending",
        refreshed.append,
        reviewer=lambda source, item: ReviewDecision(
            status="approved", reviewer="reviewer-2", reason="人工复核通过"
        ),
    )
    adapter = KnowledgeSourceAdapter(source.source_id, lambda _: html)
    approved_report = await approved.run(source, adapter)
    assert approved_report.stored == 1 and approved_report.pending_review == 0
    assert refreshed == ["occupation"]
    hits = await LocalSearchGateway(str(tmp_path / "pending")).search(
        RetrievalQuery(query="数据分析师", namespace=RetrievalNamespace.OCCUPATION)
    )
    assert hits and hits[0].metadata["reviewed_by"] == "reviewer-2"
    with pytest.raises(ValueError, match="不能处理"):
        await approved.run(
            source.model_copy(update={"source_id": "other-source"}), adapter
        )


async def test_demo_knowledge_is_traceable_hash_valid_and_searchable() -> None:
    sources_payload = json.loads(
        (DATA_DIR / "knowledge" / "sources.json").read_text(encoding="utf-8")
    )
    sources = {item["source_id"]: item for item in sources_payload["items"]}
    for path in sorted((DATA_DIR / "knowledge").glob("*.json")):
        if path.name == "sources.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "DEMO" in payload.get("_note", "")
        for item in payload["items"]:
            source = sources[item["source_id"]]
            assert source["namespace"] == item["namespace"] == path.stem
            assert item["source_url"] and item["fetched_at"]
            canonical = json.dumps(
                {
                    key: value
                    for key, value in item.items()
                    if key not in {"fetched_at", "version", "content_hash", "status"}
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == item[
                "content_hash"
            ]

    repo = LocalSearchGateway(str(DATA_DIR / "knowledge"))
    hits = await repo.search(
        RetrievalQuery(
            query="计算机专业",
            namespace=RetrievalNamespace.OCCUPATION,
            filters={"content_type": "major"},
        )
    )
    assert hits and hits[0].metadata["source_id"] == "src-chsi-major-demo"
