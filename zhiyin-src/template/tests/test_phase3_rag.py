from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine

from zhiyin_boot.container import build_container
from zhiyin_boot.settings import Settings
from zhiyin_business.policies.retrieval import RetrievalPlanningPolicy
from zhiyin_kernel.enums import LoopStage, RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery
from zhiyin_infrastructure.local.knowledge import LocalSearchGateway
from zhiyin_infrastructure.persistence.models import RetrievalDocumentRow
from zhiyin_infrastructure.persistence.retrieval_documents import RetrievalDocumentStore
from zhiyin_infrastructure.retrieval_content import (
    chunk_retrieval_document,
    load_retrieval_schema,
    validate_retrieval_document,
)


ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_contract_is_strict_and_covers_six_namespaces() -> None:
    assert {item.value for item in RetrievalNamespace} == {
        "theory",
        "occupation",
        "jd",
        "report",
        "memory",
        "resume",
    }
    with pytest.raises(ValidationError):
        RetrievalQuery(query="职业", namespace="theory", unknown=True)  # type: ignore[call-arg]


def test_planning_policy_covers_every_stage_and_scopes_private_data() -> None:
    policy = RetrievalPlanningPolicy()
    plans = {
        stage: policy.plan(
            stage=stage,
            intent="career",
            message="结合我的简历、历史报告和近期岗位给出建议",
            user_id="user-1",
            org_id="org-1",
        )
        for stage in LoopStage
    }
    assert set(plans) == set(LoopStage)
    assert all(plan.required for plan in plans.values())
    private = {"resume", "memory", "report"}
    for plan in plans.values():
        for query in plan.queries:
            if query.namespace.value in private:
                assert query.filters["user_id"] == "user-1"
                assert query.filters["org_id"] == "org-1"


def test_decision_comparison_builds_symmetric_subqueries() -> None:
    plan = RetrievalPlanningPolicy().plan(
        stage=LoopStage.DECIDE,
        intent="compare",
        message="比较后端开发和产品经理",
        user_id="user-1",
    )
    by_namespace: dict[str, set[str]] = {}
    for query in plan.queries:
        by_namespace.setdefault(query.namespace.value, set()).add(query.query)
    assert by_namespace
    assert all(targets == {"后端开发", "产品经理"} for targets in by_namespace.values())


def test_content_schema_and_chunk_ids_are_stable() -> None:
    schema = load_retrieval_schema(ROOT / "data/evaluation/retrieval_schema.json")
    document = {
        "id": "theory:test",
        "namespace": "theory",
        "source_id": "source:test",
        "title": "测试理论",
        "summary": "第一段说明。第二段说明。第三段说明。",
        "source_url": "https://example.invalid/test",
        "version": 1,
        "status": "enabled",
        "content_hash": "hash",
    }
    validate_retrieval_document(document, schema)
    first = chunk_retrieval_document(document, max_chars=12, overlap_chars=2)
    second = chunk_retrieval_document(document, max_chars=12, overlap_chars=2)
    assert first == second
    assert len(first) >= 2
    assert len({item["id"] for item in first}) == len(first)


def test_private_content_requires_tenant_and_user() -> None:
    schema = load_retrieval_schema(ROOT / "data/evaluation/retrieval_schema.json")
    document = {
        "id": "resume:test",
        "namespace": "resume",
        "source_id": "source:test",
        "content": "脱敏简历",
        "version": 1,
        "status": "enabled",
        "content_hash": "hash",
    }
    with pytest.raises(ValueError, match="org_id"):
        validate_retrieval_document(document, schema)


@pytest.mark.asyncio
async def test_authority_backfill_filters_status_expiry_and_private_scope(tmp_path: Path) -> None:
    database = tmp_path / "rag.sqlite3"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)
    RetrievalDocumentRow.__table__.create(engine)
    store = RetrievalDocumentStore(url)
    now = datetime.now(timezone.utc)
    store.upsert(
        document_id="resume:visible",
        namespace=RetrievalNamespace.RESUME,
        source_id="resume-source",
        content="数据库中的最新脱敏简历",
        org_id="org-1",
        user_id="user-1",
    )
    store.upsert(
        document_id="resume:expired",
        namespace=RetrievalNamespace.RESUME,
        source_id="expired-source",
        content="已过期",
        org_id="org-1",
        user_id="user-1",
        expire_at=now - timedelta(seconds=1),
    )
    hits = [
        RetrievalEvidence(
            evidence_id=item,
            namespace=RetrievalNamespace.RESUME,
            content="向量副本",
        )
        for item in ("resume:visible", "resume:expired")
    ]
    request = RetrievalQuery(
        query="简历",
        namespace=RetrievalNamespace.RESUME,
        org_id="org-1",
        user_id="user-1",
    )
    outcome = await store.hydrate(request, hits)
    result = outcome.hits
    assert [item.evidence_id for item in result] == ["resume:visible"]
    assert result[0].content == "数据库中的最新脱敏简历"
    # D13：被丢弃的条数必须交出来，否则调用方分不清"没命中"与"被权威门挡掉"
    assert (outcome.checked, outcome.dropped) == (2, 1)
    assert outcome.all_dropped is False
    empty = await store.hydrate(
        request.model_copy(update={"user_id": "another-user"}), hits
    )
    assert empty.hits == []
    assert empty.all_dropped is True, "全部被挡掉时必须能识别出来"
    store.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_expire_due_marks_past_deadline_documents_as_expired(tmp_path: Path) -> None:
    """已过截止时间的高时效文档必须**落状态**，而不是只在查询时被过滤（D7）。

    二者不是一回事：`_visible()` 让过期文档检不出来，但记录仍是 `enabled`——
    于是"过期内容不能进入生产索引"在索引侧不成立（向量库仍留着它），
    报表与审计也看不出它已过期。设计口径见第三期设计 §4.3。
    """
    database = tmp_path / "expire.sqlite3"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)
    RetrievalDocumentRow.__table__.create(engine)
    store = RetrievalDocumentStore(url)
    now = datetime.now(timezone.utc)
    store.upsert(
        document_id="jd:due", namespace=RetrievalNamespace.JD, source_id="jd-due",
        content="已截止的 JD", expire_at=now - timedelta(days=1),
    )
    store.upsert(
        document_id="jd:alive", namespace=RetrievalNamespace.JD, source_id="jd-alive",
        content="仍在招的 JD", expire_at=now + timedelta(days=30),
    )
    store.upsert(
        document_id="jd:no-deadline", namespace=RetrievalNamespace.JD, source_id="jd-no-deadline",
        content="长期内容，无截止时间",
    )

    assert store.expire_due(now=now) == ["jd:due"]
    # 幂等：再扫一轮没有可标记的
    assert store.expire_due(now=now) == []

    with store._sessions() as session:  # noqa: SLF001 — 直接核对落库结果
        due = session.get(RetrievalDocumentRow, "jd:due")
        alive = session.get(RetrievalDocumentRow, "jd:alive")
        no_deadline = session.get(RetrievalDocumentRow, "jd:no-deadline")
    assert due.status == "expired"
    assert due.metadata_json["expired_reason"] == "past_deadline"
    # 历史样本标记：可保留用于要求分析，但永不作为"现在可以申请"的证据
    assert due.metadata_json["historical_sample"] is True
    assert alive.status == "enabled"
    assert no_deadline.status == "enabled"
    store.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_expire_by_source_takes_down_a_removed_source(tmp_path: Path) -> None:
    """来源下架：该来源的文档整体过期，别处的文档不受影响（D7）。"""
    database = tmp_path / "takedown.sqlite3"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)
    RetrievalDocumentRow.__table__.create(engine)
    store = RetrievalDocumentStore(url)
    store.upsert(
        document_id="jd:a", namespace=RetrievalNamespace.JD, source_id="job-board-a",
        content="A 站岗位",
    )
    store.upsert(
        document_id="jd:b", namespace=RetrievalNamespace.JD, source_id="job-board-b",
        content="B 站岗位",
    )

    assert store.expire_by_source("job-board-a") == ["jd:a"]
    with store._sessions() as session:  # noqa: SLF001
        taken = session.get(RetrievalDocumentRow, "jd:a")
        other = session.get(RetrievalDocumentRow, "jd:b")
    assert taken.status == "expired"
    assert taken.metadata_json["expired_reason"] == "source_removed"
    assert other.status == "enabled"
    store.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_document_expiry_worker_reports_how_many_it_expired(tmp_path: Path) -> None:
    """Worker 的 `run_once()` 返回本轮标记数，供调度与观测使用（D7）。"""
    from zhiyin_infrastructure.workers.document_expiry import DocumentExpiryWorker

    database = tmp_path / "worker.sqlite3"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)
    RetrievalDocumentRow.__table__.create(engine)
    store = RetrievalDocumentStore(url)
    store.upsert(
        document_id="jd:stale", namespace=RetrievalNamespace.JD, source_id="s",
        content="过期", expire_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    worker = DocumentExpiryWorker(store)
    assert worker.name == "document_expiry"
    assert await worker.run_once() == 1
    assert await worker.run_once() == 0
    store.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_eval_set_expectations_are_not_yet_covered_by_the_corpus() -> None:
    """登记现状：评测集期望**尚未**被语料覆盖，因此现在算不出质量指标（D7 ⑦）。

    这是一条**状态记录型**断言，不是质量断言。它锁的事实：
    `data/evaluation/retrieval_cases.json` 里 100 条期望 id（`namespace:xxx`）
    指向一份"测试知识快照"，而该快照**不在仓库里**（`data/knowledge/` 只有
    3 条 theory + 3 条 occupation，且它们是**演示卡片**）。

    为什么要写成测试：它会在"真实内容进索引 / 补上知识快照"之后立刻变红，提醒把
    基准与门槛真正跑起来并更新本记录——否则这件事会一直悬着，而
    `evaluate_retrieval()` 也会继续没有调用方。

    ⚠️ 本用例过去还顺带记录"id 口径不一致"，但**读的是语料 JSON 而不是通道**，
    于是 D11 修好之后它仍然通过（两种形态都在语料里，裸 id 永远非空）——
    典型的"记录型断言的观测对象错了"。现在改为**实测通道返回的 id 形态**。
    """
    dataset = json.loads(
        (ROOT / "data/evaluation/retrieval_cases.json").read_text(encoding="utf-8")
    )
    expected: list[tuple[str, str]] = [
        (str(case["namespace"]), str(item))
        for case in dataset["items"]
        for item in case.get("expected_ids", [])
    ]
    assert expected, "评测集必须有非空期望"

    corpus: dict[str, set[str]] = {}
    for path in sorted((ROOT / "data/knowledge").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else (payload.get("items") or [])
        for item in items:
            if not item.get("id"):
                continue
            namespace = str(item.get("namespace") or path.stem)
            corpus.setdefault(namespace, set()).add(f"{namespace}:{item['id']}")

    covered = [pair for pair in expected if pair[1] in corpus.get(pair[0], set())]
    assert not covered, (
        f"评测集期望已被语料覆盖 {len(covered)} 条——说明真实内容或测试知识快照已就位。"
        "请跑 `python scripts/eval_retrieval.py` 出新的基准报告，并按第三期 §12.3 "
        "冻结质量门槛，然后更新本用例与《检索质量基准》文档。"
    )

    # D11 已收口：期望与**通道实测**口径一致（都在此锁定，防止回退成裸 id）
    assert all(":" in item for _, item in expected), "评测集期望应统一为 namespace:id"
    gateway = LocalSearchGateway(str(ROOT / "data/knowledge"))
    hits = await gateway.search(
        RetrievalQuery(
            query="霍兰德", namespace=RetrievalNamespace.THEORY, top_k=3
        )
    )
    assert hits, "本地语料应能召回（用于观测通道 id 口径）"
    assert all(
        hit.evidence_id.startswith("theory:") for hit in hits
    ), f"D11 回退：通道返回了裸 id {[hit.evidence_id for hit in hits]}"


@pytest.mark.asyncio
async def test_demo_namespaces_are_detected_from_the_authority_store(tmp_path: Path) -> None:
    """权威表要能回答"哪些 namespace 的内容是演示的"（D12 装配期信号）。

    为什么这条重要：装配期信号原先只看检索通道实现，切到 PAMI 后本地通道退出链路，
    于是 `/healthz` 报 `demo_content=[]`、`status=ok`，而权威表里全是 demo——系统仍在
    用演示内容却自称没事。检测必须落在**内容的事实来源**上。
    """
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'demo.sqlite3').as_posix()}"
    sync_url = f"sqlite:///{(tmp_path / 'demo.sqlite3').as_posix()}"
    engine = create_engine(sync_url)
    from zhiyin_infrastructure.persistence.models import Base

    Base.metadata.create_all(engine)
    engine.dispose()

    store = RetrievalDocumentStore(database_url)
    store.upsert(
        document_id="theory:demo-doc",
        namespace=RetrievalNamespace.THEORY,
        source_id="demo-doc",
        content="演示理论卡",
        metadata={"demo": True},
    )
    store.upsert(
        document_id="theory:real-doc",
        namespace=RetrievalNamespace.THEORY,
        source_id="real-doc",
        content="真实来源",
        metadata={"demo": False},
    )
    store.upsert(
        document_id="occupation:demo-occ",
        namespace=RetrievalNamespace.OCCUPATION,
        source_id="demo-occ",
        content="演示职业条目",
        metadata={"demo": True},
    )
    assert store.demo_namespaces() == ["occupation", "theory"]

    # 过期/禁用后不再计入（演示内容下架后信号应消失）
    store.expire_by_source("demo-occ")
    assert store.demo_namespaces() == ["theory"]
    store.close()


def test_fixed_evaluation_set_has_100_nonempty_cases_and_full_coverage() -> None:
    payload = json.loads(
        (ROOT / "data/evaluation/retrieval_cases.json").read_text(encoding="utf-8")
    )
    cases = payload["items"]
    assert len(cases) == 100
    assert {case["stage"] for case in cases} == {stage.value for stage in LoopStage}
    assert {case["namespace"] for case in cases} == {
        item.value for item in RetrievalNamespace
    }
    assert all(case["query"].strip() and case["expected_ids"] for case in cases)


@pytest.mark.asyncio
async def test_phase3_container_keeps_authority_as_internal_extra(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'phase3.sqlite3').as_posix()}"
    container = build_container(
        Settings(
            database_url=database_url,
            use_mysql=True,
            # 本用例只验检索装配，未接真实模型；按 D1 需显式许可占位实现。
            allow_placeholder_llm=True,
            use_pami_embedding=True,
            pami_base_url="http://127.0.0.1:8081",
            pami_embedding_model_id="test-model",
            use_pgvector=True,
            vector_database_url="postgresql://test:test@127.0.0.1:5432/test",
            redis_url="",
        )
    )
    assert container.extra["retrieval_authority"] is not None
    assert container.search is not None
    container.extra["retrieval_authority"].close()
    container.transactions.close()
    await container.extra["database_context"].close()
