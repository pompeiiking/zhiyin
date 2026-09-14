"""基础设施层测试：语义必须与 MySQL 版一致。

本文件的自述原则是「行为必须与 MySQL 版一致（含版本 +1、只追加、影响面匹配），
否则切真后会暴露契约之外的差异」。这里把这些语义逐条钉住。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from zhiyin_kernel.assets import ActionPhase, ActionPlan, ActionTask
from zhiyin_kernel.blackboard import (
    AssetVersion,
    BehaviorLog,
    ProfileField,
)
from zhiyin_kernel.enums import (
    AssetType,
    BehaviorEventType,
    LoopStage,
    ProfileSource,
    TaskStatus,
)
from zhiyin_kernel.identity import UserAccount

from zhiyin_infrastructure.local.feature_flag import LocalFeatureFlagStore
from zhiyin_infrastructure.local.knowledge import LocalKnowledgeRepo
from zhiyin_infrastructure.local.llm import synthesize_from_schema
from zhiyin_infrastructure.local.object_store import LocalFileStore
from zhiyin_infrastructure.local.repository import (
    InMemoryAssetRepository,
    InMemoryBehaviorRepository,
    InMemoryProfileRepository,
    InMemoryTaskSessionRepository,
    LocalJsonRegistryRepository,
)
from zhiyin_infrastructure.persistence.models import (
    BACKEND_DYNAMIC_TABLES,
    CORE_TABLES,
    FRONTEND_DYNAMIC_TABLES,
    TABLE_INVENTORY,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# 画像
# --------------------------------------------------------------------------


async def test_profile_upsert_is_idempotent_by_key() -> None:
    repo = InMemoryProfileRepository()
    await repo.upsert_field(
        "u1",
        ProfileField(
            key="major",
            value="计算机",
            confidence=0.9,
            source=ProfileSource.CONVERSATION,
            updated_at=_now(),
        ),
    )
    await repo.upsert_field(
        "u1",
        ProfileField(
            key="major",
            value="软件工程",
            confidence=1.0,
            source=ProfileSource.RESUME,
            updated_at=_now(),
        ),
    )

    fields = await repo.list_fields("u1")
    assert len(fields) == 1
    assert fields[0].value == "软件工程"


async def test_profile_version_increases_on_update() -> None:
    repo = InMemoryProfileRepository()
    field = ProfileField(
        key="interest",
        value="a",
        confidence=1.0,
        source=ProfileSource.CONVERSATION,
        updated_at=_now(),
    )
    await repo.upsert_field("u1", field)
    v1 = (await repo.get("u1")).version
    await repo.upsert_field("u1", field)
    v2 = (await repo.get("u1")).version
    assert v2 > v1


async def test_profile_read_is_a_snapshot() -> None:
    repo = InMemoryProfileRepository()
    await repo.upsert_field(
        "u1",
        ProfileField(
            key="k",
            value={"nested": 1},
            confidence=1.0,
            source=ProfileSource.CONVERSATION,
            updated_at=_now(),
        ),
    )
    snapshot = (await repo.list_fields("u1"))[0]
    snapshot.value["nested"] = 999
    assert (await repo.list_fields("u1"))[0].value["nested"] == 1


# --------------------------------------------------------------------------
# 行为日志
# --------------------------------------------------------------------------


async def test_behavior_log_is_append_only_and_sorted_desc() -> None:
    repo = InMemoryBehaviorRepository()
    for index in range(3):
        await repo.append(
            BehaviorLog(
                id="",
                user_id="u1",
                event_type=BehaviorEventType.ANSWER,
                occurred_at=datetime(2026, 9, 14, index, tzinfo=timezone.utc),
            )
        )

    logs = await repo.list_by_user("u1")
    assert len(logs) == 3
    # 最近的在最前
    assert logs[0].occurred_at > logs[-1].occurred_at
    # 没有提供任何 UPDATE 路径
    assert not hasattr(repo, "update")


async def test_behavior_filters_and_last_occurred() -> None:
    repo = InMemoryBehaviorRepository()
    await repo.append(
        BehaviorLog(
            id="",
            user_id="u1",
            event_type=BehaviorEventType.TASK_DONE,
            occurred_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        )
    )
    await repo.append(
        BehaviorLog(
            id="",
            user_id="u1",
            event_type=BehaviorEventType.TASK_DONE,
            occurred_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        )
    )

    only_done = await repo.list_by_user("u1", event_types=[BehaviorEventType.TASK_DONE])
    assert len(only_done) == 2
    assert await repo.last_occurred_at("u1", BehaviorEventType.TASK_DONE) == datetime(
        2026, 9, 13, tzinfo=timezone.utc
    )
    # 停滞检测的唯一依据（FR-REVIEW-001）
    assert await repo.last_occurred_at("u1", BehaviorEventType.GAP_CLAIM) is None


# --------------------------------------------------------------------------
# 资产与影响面
# --------------------------------------------------------------------------


def _asset(user_id: str, asset_type: AssetType, keys: list[str], version: int = 1) -> AssetVersion:
    return AssetVersion(
        id="",
        user_id=user_id,
        asset_type=asset_type,
        version=version,
        created_at=_now(),
        depends_on_profile_keys=keys,
    )


async def test_asset_version_is_monotonic() -> None:
    repo = InMemoryAssetRepository()
    first = await repo.save_version(_asset("u1", AssetType.REPORT, ["major"]))
    # 调用方就算传小值，也不会把版本压回去
    second = await repo.save_version(
        _asset("u1", AssetType.REPORT, ["major"], version=0)
    )

    assert first.version == 1
    assert second.version == 2


async def test_affected_assets_only_matches_dependencies() -> None:
    repo = InMemoryAssetRepository()
    await repo.save_version(_asset("u1", AssetType.REPORT, ["major", "interest"]))
    await repo.save_version(_asset("u1", AssetType.ACTION_PLAN, ["target_city"]))

    hit = await repo.list_affected_assets("u1", ["major"])
    assert [item.asset_type for item in hit] == [AssetType.REPORT]

    miss = await repo.list_affected_assets("u1", ["something_else"])
    assert miss == []


async def test_affected_assets_uses_latest_version_only() -> None:
    """只重算最新版本，避免把历史版本也卷进影响面传播。"""
    repo = InMemoryAssetRepository()
    await repo.save_version(_asset("u1", AssetType.REPORT, ["major"]))
    latest = await repo.save_version(_asset("u1", AssetType.REPORT, ["major"]))

    hit = await repo.list_affected_assets("u1", ["major"])
    assert len(hit) == 1
    assert hit[0].version == latest.version


async def test_select_direction_plan_is_revocable() -> None:
    from zhiyin_kernel.assets import DirectionPlan
    from zhiyin_kernel.enums import PlanRole

    repo = InMemoryAssetRepository()
    await repo.save_direction_plans(
        "u1",
        [
            DirectionPlan(
                id="p1",
                role=PlanRole.MAIN,
                name="主攻",
                target_desc="",
                match_score=0.8,
                fit_reason="",
                main_risk="",
            ),
            DirectionPlan(
                id="p2",
                role=PlanRole.FALLBACK,
                name="保底",
                target_desc="",
                match_score=0.5,
                fit_reason="",
                main_risk="",
            ),
        ],
    )

    await repo.select_direction_plan("u1", "p1")
    plans = await repo.list_direction_plans("u1")
    assert [plan.selected for plan in plans] == [True, False]

    # 可撤回：改选另一个，前一个必须被取消
    await repo.select_direction_plan("u1", "p2")
    plans = await repo.list_direction_plans("u1")
    assert [plan.selected for plan in plans] == [False, True]


async def test_mark_task_done() -> None:
    repo = InMemoryAssetRepository()
    await repo.save_action_plan(
        "u1",
        ActionPlan(
            id="ap1",
            phases=[
                ActionPhase(
                    name="阶段一",
                    date_range="9月",
                    tasks=[ActionTask(text="改简历"), ActionTask(text="投 3 家")],
                )
            ],
        ),
    )

    plan = await repo.mark_task_done("u1", "改简历")
    assert plan.phases[0].tasks[0].done is True
    assert plan.phases[0].tasks[0].done_at is not None
    assert plan.phases[0].tasks[1].done is False

    with pytest.raises(LookupError):
        await repo.mark_task_done("u1", "不存在的任务")


# --------------------------------------------------------------------------
# 会话
# --------------------------------------------------------------------------


async def test_task_session_find_active_and_update_stage() -> None:
    from zhiyin_kernel.blackboard import TaskSession

    repo = InMemoryTaskSessionRepository()
    await repo.create(
        TaskSession(
            id="s1",
            user_id="u1",
            task_code="confused",
            task_name="迷茫",
            loop_stage=LoopStage.COLLECT,
            lead_agent="profile_analyst",
            created_at=_now(),
            updated_at=_now(),
        )
    )

    assert (await repo.find_active("u1", "confused")).id == "s1"

    await repo.update_stage("s1", LoopStage.DIAGNOSE, "career_advisor")
    assert (await repo.get("s1")).loop_stage is LoopStage.DIAGNOSE

    await repo.update_status("s1", TaskStatus.COMPLETED)
    assert await repo.find_active("u1", "confused") is None


async def test_user_repository() -> None:
    from zhiyin_infrastructure.local.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()
    await repo.create(
        UserAccount(id="demo-user-0001", phone="DEMO-000", nickname="演示同学", created_at=_now())
    )
    assert (await repo.get_by_id("demo-user-0001")).nickname == "演示同学"
    assert (await repo.get_by_phone("DEMO-000")).id == "demo-user-0001"
    await repo.touch_last_login("demo-user-0001", _now())
    assert (await repo.get_by_id("demo-user-0001")).last_login_at is not None


# --------------------------------------------------------------------------
# 动态资源
# --------------------------------------------------------------------------


async def test_registry_reads_seed_data() -> None:
    repo = LocalJsonRegistryRepository(str(DATA_DIR / "registry"))

    agents = await repo.list_agents()
    assert len(agents) == 5
    assert (await repo.get_agent("profile_analyst")).name == "建档分析师"

    entries = await repo.list_task_entries()
    assert [entry.code for entry in entries][:2] == ["confused", "verify_direction"]
    # sort_order 必须生效，否则首页任务顺序不稳定
    assert [entry.sort_order for entry in entries] == sorted(
        entry.sort_order for entry in entries
    )
    # 「直接开聊」没有目标环节，由编排器判定
    assert entries[-1].target_stage is None

    assert await repo.get_theory_card("holland_riasec") is not None
    assert len(await repo.list_theory_cards(["casve", "clover"])) == 2


async def test_registry_missing_dir_is_empty_not_crash() -> None:
    repo = LocalJsonRegistryRepository(str(DATA_DIR / "does-not-exist"))
    assert await repo.list_agents() == []
    assert await repo.get_agent("any") is None


def test_feature_flags_come_from_json() -> None:
    store = LocalFeatureFlagStore(str(DATA_DIR / "registry"))
    flags = store.all()
    assert flags["report_full_text"] is True
    assert flags["export"] is False
    # 未知开关默认关闭，避免"配置漏了反而打开"
    assert store.is_enabled("not_configured") is False


# --------------------------------------------------------------------------
# 模型 Mock
# --------------------------------------------------------------------------


def test_mock_llm_synthesizes_schema_valid_payload() -> None:
    schema = {
        "type": "object",
        "required": ["kind", "nested"],
        "properties": {
            "kind": {"enum": ["a", "b"]},
            "nested": {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string", "minLength": 3}},
            },
        },
    }
    payload = synthesize_from_schema(schema)
    assert payload["kind"] == "a"
    assert len(payload["nested"]["name"]) >= 3


def test_mock_llm_skips_nullable_optional_fields() -> None:
    """可空可选字段必须跳过，否则 Mock 会凭空造出"换主理告知"这类内容。"""
    schema = {
        "type": "object",
        "required": ["must"],
        "properties": {
            "must": {"anyOf": [{"type": "null"}, {"type": "string"}]},
            "maybe": {"anyOf": [{"type": "null"}, {"type": "string"}]},
            "always": {"type": "string"},
        },
    }
    payload = synthesize_from_schema(schema)
    assert isinstance(payload["must"], str)
    assert "maybe" not in payload
    assert "always" in payload


def test_mock_llm_handles_refs() -> None:
    schema = {
        "type": "object",
        "required": ["item"],
        "properties": {"item": {"$ref": "#/$defs/Item"}},
        "$defs": {
            "Item": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            }
        },
    }
    payload = synthesize_from_schema(schema)
    assert "id" in payload["item"]


# --------------------------------------------------------------------------
# 对象存储 / 知识库
# --------------------------------------------------------------------------


async def test_local_file_store_roundtrip(tmp_path) -> None:
    store = LocalFileStore(str(tmp_path / "objects"))
    key = store.build_key("u1", "report", 2, ".pdf")

    await store.put(key, b"hello", content_type="application/pdf")
    assert await store.get(key) == b"hello"
    stat = await store.stat(key)
    assert stat.size == 5

    await store.delete(key)
    assert await store.stat(key) is None


async def test_local_file_store_blocks_path_traversal(tmp_path) -> None:
    store = LocalFileStore(str(tmp_path / "objects"))
    with pytest.raises(ValueError):
        await store.put("../escape.txt", b"x")


async def test_knowledge_search_ranks_and_respects_namespace() -> None:
    repo = LocalKnowledgeRepo(str(DATA_DIR / "knowledge"))
    hits = await repo.search("霍兰德", namespace="theory", top_k=3)
    assert hits, "应能在 theory 命名空间命中霍兰德相关条目"
    assert hits[0].metadata["namespace"] == "theory"

    # 公共知识命中必须带来源与抓取时间，供报告溯源（R-CRAWL-006）
    assert "source_url" in hits[0].metadata
    assert "fetched_at" in hits[0].metadata


async def test_knowledge_search_vector_degrades_to_empty() -> None:
    from zhiyin_infrastructure.local.knowledge import LocalKeywordSearch

    search = LocalKeywordSearch(str(DATA_DIR / "knowledge"))
    assert await search.vector([0.1, 0.2]) == []
    assert await search.hybrid("霍兰德", top_k=2) == await search.keyword("霍兰德", top_k=2)


# --------------------------------------------------------------------------
# 表清单
# --------------------------------------------------------------------------


def test_table_inventory_covers_documented_scope() -> None:
    """表清单必须覆盖文档口径，而不是只列核心表。

    修复前 TABLE_INVENTORY 只有 21 张，缺 17+ 张动态资源表，
    等于把"动态资源入库"这条验收口径悬空了。
    """
    assert len(CORE_TABLES) >= 19
    assert len(FRONTEND_DYNAMIC_TABLES) == 13
    assert len(BACKEND_DYNAMIC_TABLES) == 25

    # 共享表只计一次
    assert len(TABLE_INVENTORY) == len(
        set(CORE_TABLES) | set(FRONTEND_DYNAMIC_TABLES) | set(BACKEND_DYNAMIC_TABLES)
    )

    for name in (
        "prompt_template",
        "workflow_template",
        "decision_rule",
        "handoff_rule",
        "event_rule",
        "schedule_rule",
        "notify_template",
        "knowledge_source",
        "feature_flag",
        "app_page",
        "app_copy",
    ):
        assert name in TABLE_INVENTORY, f"表清单缺少动态资源表：{name}"


def test_table_inventory_has_no_duplicates() -> None:
    assert len(TABLE_INVENTORY) == len(set(TABLE_INVENTORY))
