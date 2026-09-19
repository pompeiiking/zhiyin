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
    result = await store.hydrate(request, hits)
    assert [item.evidence_id for item in result] == ["resume:visible"]
    assert result[0].content == "数据库中的最新脱敏简历"
    assert await store.hydrate(
        request.model_copy(update={"user_id": "another-user"}), hits
    ) == []
    store.close()
    engine.dispose()


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
