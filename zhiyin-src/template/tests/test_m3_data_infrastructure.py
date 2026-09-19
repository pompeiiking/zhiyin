from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from zhiyin_data_sdk.errors import ValidationError
from zhiyin_data_sdk.gateways.ai import SearchGateway
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery
from zhiyin_data_sdk.gateways.vector import VectorRecord
from zhiyin_infrastructure.local.embedding import LocalHashEmbedder
from zhiyin_infrastructure.local.vector_store import LocalVectorStore
from zhiyin_infrastructure.mysql import SqlAlchemyRawQueryGateway
from zhiyin_infrastructure.persistence.database import SqlAlchemyTransactionManager
from zhiyin_infrastructure.persistence.embed_tasks import EmbedTaskStore
from zhiyin_infrastructure.mysql.repositories import DatabaseContext
from zhiyin_infrastructure.pgvector import PgVectorGateway
from zhiyin_infrastructure.search import RrfHybridSearchGateway
from zhiyin_infrastructure.workers.vector_sync import VectorSyncWorker


class FakeVectorPool:
    def __init__(self) -> None:
        self.upsert_rows: list[tuple[Any, ...]] = []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        assert "ON CONFLICT" in sql
        self.upsert_rows.extend(rows)

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.calls.append((sql, args))
        return [
            {
                "record_id": "doc-1",
                "text": "职业兴趣",
                "source_id": "source-1",
                "metadata": {"reviewed": True},
                "score": 0.91,
            }
        ]

    async def execute(self, sql: str, *args: Any) -> str:
        self.calls.append((sql, args))
        return "DELETE 2"


@pytest.mark.asyncio
async def test_pgvector_gateway_preserves_namespace_model_and_metadata() -> None:
    pool = FakeVectorPool()
    gateway = PgVectorGateway("postgresql://example/test", pool=pool)
    record = VectorRecord(
        id="doc-1",
        vector=[0.1] * 1024,
        text="职业兴趣",
        source_id="source-1",
        metadata={"reviewed": True},
    )

    assert await gateway.upsert("theory", [record], model="embed-v1") == 1
    hits = await gateway.search(
        "theory",
        [0.1] * 1024,
        model="embed-v1",
        filters={"reviewed": True},
    )

    assert pool.upsert_rows[0][:3] == ("theory", "doc-1", "embed-v1")
    assert hits[0].source_id == "source-1"
    assert hits[0].metadata == {"reviewed": True}


@pytest.mark.asyncio
async def test_pgvector_gateway_decodes_asyncpg_jsonb_string() -> None:
    pool = FakeVectorPool()

    async def fetch_with_string_metadata(sql: str, *args: Any) -> list[dict[str, Any]]:
        return [
            {
                "record_id": "doc-1",
                "text": "职业兴趣",
                "source_id": "source-1",
                "metadata": '{"reviewed": true}',
                "score": 0.91,
            }
        ]

    pool.fetch = fetch_with_string_metadata  # type: ignore[method-assign]
    gateway = PgVectorGateway("postgresql://example/test", pool=pool)

    hits = await gateway.search("theory", [0.1] * 1024, model="embed-v1")

    assert hits[0].metadata == {"reviewed": True}


@pytest.mark.asyncio
async def test_pgvector_gateway_rejects_unknown_namespace_and_dimension() -> None:
    gateway = PgVectorGateway("postgresql://example/test", pool=FakeVectorPool())
    with pytest.raises(ValidationError, match="命名空间"):
        await gateway.search("unknown", [0.0] * 1024, model="embed-v1")
    with pytest.raises(ValidationError, match="1024"):
        await gateway.search("theory", [0.0] * 3, model="embed-v1")


@pytest.mark.asyncio
async def test_raw_query_allows_dml_and_blocks_ddl() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    gateway = SqlAlchemyRawQueryGateway("mysql://unused", engine=engine)
    async with engine.begin() as connection:
        await connection.exec_driver_sql(
            "CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )

    assert await gateway.execute(
        "INSERT INTO sample (id, value) VALUES (:id, :value)",
        {"id": 1, "value": "ok"},
    ) == 1
    assert await gateway.fetch_one("SELECT * FROM sample WHERE id = :id", {"id": 1}) == {
        "id": 1,
        "value": "ok",
    }
    with pytest.raises(ValidationError, match="INSERT"):
        await gateway.execute("DROP TABLE sample")
    await gateway.close()


def test_transaction_manager_commits_and_rolls_back(tmp_path: Path) -> None:
    database = tmp_path / "transactions.sqlite3"
    url = f"sqlite:///{database.as_posix()}"
    manager = SqlAlchemyTransactionManager(url)

    with manager.begin() as transaction:
        transaction.session.execute(text("CREATE TABLE sample (value TEXT NOT NULL)"))
        transaction.session.execute(text("INSERT INTO sample VALUES ('committed')"))

    with pytest.raises(RuntimeError):
        with manager.begin() as transaction:
            transaction.session.execute(text("INSERT INTO sample VALUES ('rolled-back')"))
            raise RuntimeError("rollback")

    with create_engine(url).connect() as connection:
        values = connection.execute(text("SELECT value FROM sample")).scalars().all()
    assert values == ["committed"]
    manager.close()


class FakeKeywordSearch(SearchGateway):
    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        return [
            RetrievalEvidence(
                evidence_id="shared", namespace=request.namespace,
                content="共同命中", score=10
            ),
            RetrievalEvidence(
                evidence_id="keyword", namespace=request.namespace,
                content="关键词命中", score=9
            ),
        ][:request.top_k]


@pytest.mark.asyncio
async def test_rrf_hybrid_search_merges_both_channels() -> None:
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    shared_vector, vector_only = await embedding.embed(["目标", "向量"])
    await vector.upsert(
        "theory",
        [
            VectorRecord(id="shared", vector=shared_vector, text="共同命中"),
            VectorRecord(id="vector", vector=vector_only, text="向量命中"),
        ],
        model=embedding.model_id,
    )
    search = RrfHybridSearchGateway(FakeKeywordSearch(), embedding, vector, rrf_k=60)

    hits = await search.search(
        RetrievalQuery(
            query="目标", namespace=RetrievalNamespace.THEORY, top_k=3
        )
    )

    assert hits[0].evidence_id == "shared"
    assert hits[0].metadata["retrieval"]["ranks"] == {"keyword": 1, "vector": 1}
    assert {hit.evidence_id for hit in hits} == {"shared", "keyword", "vector"}


@pytest.mark.asyncio
async def test_vector_sync_worker_upserts_and_deletes_idempotently() -> None:
    context = DatabaseContext("sqlite+aiosqlite:///:memory:", auto_create=True)
    tasks = EmbedTaskStore(context)
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    worker = VectorSyncWorker(tasks, embedding, vector)
    await tasks.enqueue(
        namespace="theory",
        source_id="doc-1",
        model="test-model",
        content_hash="hash-1",
        text="职业兴趣",
        metadata={"reviewed": True},
    )

    assert await worker.run_once() == 1
    query = (await embedding.embed(["职业兴趣"]))[0]
    assert [hit.id for hit in await vector.search("theory", query, model="test-model")] == [
        "doc-1"
    ]
    assert await worker.run_once() == 0

    await tasks.enqueue(
        namespace="theory",
        source_id="doc-1",
        model="test-model",
        content_hash="hash-delete",
        operation="delete",
    )
    assert await worker.run_once() == 1
    assert await vector.search("theory", query, model="test-model") == []
    await context.close()
