from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from zhiyin_data_sdk.errors import ValidationError
from zhiyin_data_sdk.gateways.ai import EmbedGateway, SearchGateway
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery
from zhiyin_data_sdk.gateways.vector import VectorGateway, VectorHit, VectorRecord
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
    """模拟真实关键词通道：同样按 `namespace:id` 出 id（D11 后的统一口径）。

    裸 id 是 D11 之前的本地实现行为；假件必须跟真实通道保持同一口径，否则这里
    会掩盖跨通道去重失效的问题。
    """

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        prefix = request.namespace.value
        return [
            RetrievalEvidence(
                evidence_id=f"{prefix}:shared", namespace=request.namespace,
                content="共同命中", score=10
            ),
            RetrievalEvidence(
                evidence_id=f"{prefix}:keyword", namespace=request.namespace,
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

    # 两条通道都用 `namespace:id`：同一篇文档（shared）必须**只出现一次**且带上
    # 两条通道的排名——这就是 D11 要锁的不变式。裸 id 时代它会变成两条重复证据。
    assert hits[0].evidence_id == "theory:shared"
    assert hits[0].metadata["retrieval"]["ranks"] == {"keyword": 1, "vector": 1}
    assert [hit.evidence_id for hit in hits] == [
        "theory:shared", "theory:keyword", "theory:vector",
    ]
    assert len({hit.evidence_id for hit in hits}) == len(hits)


@pytest.mark.asyncio
async def test_bare_vector_ids_are_namespace_qualified_idempotently() -> None:
    """向量库里的**裸 id 旧数据**读出来要自动补齐 namespace，且不会叠加两次。"""
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    vec, = await embedding.embed(["目标"])
    await vector.upsert(
        "theory",
        [
            VectorRecord(id="legacy-bare", vector=vec, text="旧数据裸 id"),
            VectorRecord(id="theory:already", vector=vec, text="已带前缀"),
        ],
        model=embedding.model_id,
    )
    search = RrfHybridSearchGateway(EmptyKeywordSearch(), embedding, vector, rrf_k=60)
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=5)
    )
    ids = {hit.evidence_id for hit in hits}
    assert "theory:legacy-bare" in ids
    assert "theory:already" in ids, "已带前缀的 id 不得变成 theory:theory:already"
    assert not any(hit.evidence_id.startswith("theory:theory:") for hit in hits)


class FailingKeywordSearch(SearchGateway):
    """关键词 / PAMI RAG 通道不可用（ES 或平台 RAG 宕掉时就是这条）。"""

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        raise RuntimeError("keyword channel down")


class EmptyKeywordSearch(SearchGateway):
    """通道可用但无命中（"无结果"流程，与"故障"是两件事）。"""

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        return []


class FailingEmbedding(EmbedGateway):
    """Embedding 不可用（嵌入服务宕机 / 配额耗尽 / 模型下线）。"""

    model_id = "failing-model"

    async def embed(
        self, texts: list[str], *, timeout_s: float = 30.0
    ) -> list[list[float]]:
        raise RuntimeError("embedding down")


class LeakyKeywordSearch(SearchGateway):
    """异常消息里带"口令"的通道——用来验证消息不会被写进检索元数据。"""

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        raise RuntimeError("connect failed: dsn=postgresql://u:SECRET-DO-NOT-LEAK@h/db")


class RejectingPool:
    """维度不匹配时 `PgVectorGateway` 在**连接之前**就会抛 ValidationError。

    这里放一个"一旦被调用就是失败"的池子，用来证明异常确实来自入参校验而非网络。
    """

    async def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        raise AssertionError("维度校验应在连接之前拒绝，不该走到连接池")

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        raise AssertionError("维度校验应在连接之前拒绝，不该走到连接池")

    async def execute(self, sql: str, *args: Any) -> str:
        raise AssertionError("维度校验应在连接之前拒绝，不该走到连接池")


class UnreachablePool:
    """真实的"连不上"面：驱动层抛 OSError，网关须包成 UnavailableError。"""

    async def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        raise OSError("network unreachable")

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        raise OSError("network unreachable")

    async def execute(self, sql: str, *args: Any) -> str:
        raise OSError("network unreachable")


class AuditSpy:
    """与生产同形状的审计接收方，只记不写库。

    为什么要用审计来判断降级：命中全被权威门挡掉时**没有任何命中**可承载 metadata，
    审计是唯一还能说话的通道（D13）。
    """

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.records.append(kwargs)

    @property
    def last_degraded(self) -> bool | None:
        return self.records[-1]["degraded"] if self.records else None

    @property
    def last_reason(self) -> str | None:
        """最近一次审计的降级原因（`""` / `channels` / `authority_drop` / 两者）。"""
        return self.records[-1].get("degraded_reason") if self.records else None


class FailingVector(VectorGateway):
    """pgvector 不可用（库连不上 / 表被锁 / 向量维度不匹配）。"""

    async def upsert(
        self, namespace: str, records: Sequence[VectorRecord], *, model: str
    ) -> int:
        raise RuntimeError("vector down")

    async def search(
        self,
        namespace: str,
        vector: Sequence[float],
        *,
        model: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        raise RuntimeError("vector down")

    async def delete(self, namespace: str, ids: Sequence[str]) -> int:
        raise RuntimeError("vector down")

    async def clear_namespace(self, namespace: str) -> None:
        raise RuntimeError("vector down")


@pytest.mark.asyncio
async def test_keyword_channel_fault_degrades_to_vector_only() -> None:
    """故障注入：关键词 / PAMI RAG 通道不可用 → 向量通道照常出结果并如实标记降级。

    这是"ES / 平台 RAG 挂掉"的故障面。要点是**降级必须可识别**：结果里
    `retrieval.degraded_channels` 要写明哪条通道掉了，不能让调用方以为结果完整。
    """
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    vector_vector, other = await embedding.embed(["目标", "别的"])
    await vector.upsert(
        "theory",
        [
            VectorRecord(id="vector", vector=vector_vector, text="向量命中"),
            VectorRecord(id="other", vector=other, text="其它"),
        ],
        model=embedding.model_id,
    )
    search = RrfHybridSearchGateway(FailingKeywordSearch(), embedding, vector, rrf_k=60)

    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    ids = {hit.evidence_id for hit in hits}
    assert "theory:vector" in ids, "向量通道仍在工作，应能召回"
    assert "theory:keyword" not in ids, "关键词通道已故障，不应出现它的命中"
    retrieval = hits[0].metadata["retrieval"]
    assert retrieval["degraded_channels"] == ["keyword"]
    assert retrieval["degraded_reasons"] == {"keyword": "RuntimeError"}


@pytest.mark.asyncio
async def test_degradation_reason_tells_config_error_apart_from_outage() -> None:
    """降级原因要能分辨"配置错"与"连不上"——否则排查会被自己骗。

    真实教训（2026-09-19 容器内故障注入探针）：探针用 8 维向量去查要求 1024 维的
    `PgVectorGateway`，该网关在**连接之前**就抛 `ValidationError`。于是探针把
    "健康但维度不匹配"误判成"向量库宕机"，同时"死主机"用例根本没走到网络——
    一个假故障掩盖了另一个假故障。若 metadata 里只有 `degraded_channels`，
    这两种情况在结果里完全同形，而处置动作完全不同（改配置 vs 重启依赖）。

    这里锁两件事：1) 维度不匹配 -> `ValidationError`；2) 真连不上 -> `UnavailableError`。
    """
    # 情况一：配置错——向量维度与库不一致（真实 PgVectorGateway 在连接前就拒绝）
    wrong_dim = PgVectorGateway(
        "postgresql://example/test",
        pool=RejectingPool(),
    )
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), LocalHashEmbedder(dim=8, model_id="probe"), wrong_dim, rrf_k=60
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    retrieval = hits[0].metadata["retrieval"]
    assert retrieval["degraded_channels"] == ["vector"]
    assert retrieval["degraded_reasons"] == {"vector": "ValidationError"}

    # 情况二：依赖不可用——连不上向量库（维度必须合规，否则先被校验拦住）
    down = PgVectorGateway("postgresql://example/test", pool=UnreachablePool())
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), LocalHashEmbedder(dim=1024, model_id="probe"), down, rrf_k=60
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    retrieval = hits[0].metadata["retrieval"]
    assert retrieval["degraded_reasons"] == {"vector": "UnavailableError"}


@pytest.mark.asyncio
async def test_degradation_reasons_carry_no_secrets() -> None:
    """降级原因只写异常类名，绝不写异常消息——消息可能带 DSN / 口令 / 上游地址。

    检索 metadata 会随报告与接口响应外流，属《AGENTS.md》§10 的"秘密不得进入
    日志与响应"。这条用"带口令的异常消息"直接验：类名留下、口令不得出现。
    """
    embedding = LocalHashEmbedder(dim=4, model_id="probe")
    vector = LocalVectorStore()
    seeded, _ = await embedding.embed(["目标", "别的"])
    await vector.upsert(
        "theory",
        [VectorRecord(id="vector", vector=seeded, text="向量命中")],
        model=embedding.model_id,
    )
    search = RrfHybridSearchGateway(
        LeakyKeywordSearch(), embedding, vector, rrf_k=60
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    retrieval = hits[0].metadata["retrieval"]
    assert retrieval["degraded_reasons"] == {"keyword": "RuntimeError"}
    assert "SECRET-DO-NOT-LEAK" not in json.dumps(retrieval, ensure_ascii=False)


@pytest.mark.asyncio
async def test_embedding_fault_degrades_to_keyword_only() -> None:
    """故障注入：Embedding 不可用 → 关键词通道照常出结果。"""
    vector = LocalVectorStore()
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), FailingEmbedding(), vector, rrf_k=60
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert {hit.evidence_id for hit in hits} == {"theory:shared", "theory:keyword"}
    assert hits[0].metadata["retrieval"]["degraded_channels"] == ["vector"]
    assert hits[0].metadata["retrieval"]["degraded_reasons"] == {"vector": "RuntimeError"}


@pytest.mark.asyncio
async def test_degraded_reason_in_audit_tells_channel_fault_from_authority_drop() -> None:
    """审计原因要能区分"通道故障"与"命中被权威门丢"（D13 残留）。

    实测中卡过一次：真实对话里检索恒为 0，而审计只有 `degraded=1` 一个布尔，
    无法判断该去查通道/平台，还是去查权威表有没有内容。
    """
    vector = LocalVectorStore()

    # 混合模式下只挂向量通道（单通道全挂会按设计显式抛出，到不了审计）
    spy = AuditSpy()
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), FailingEmbedding(), vector, rrf_k=60, audit=spy
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=2)
    )
    assert hits, "关键词通道仍有命中"
    assert spy.last_reason == "channels"


@pytest.mark.asyncio
async def test_pgvector_fault_degrades_to_keyword_only() -> None:
    """故障注入：pgvector 不可用（嵌入正常）→ 关键词通道照常出结果。"""
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), embedding, FailingVector(), rrf_k=60
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert {hit.evidence_id for hit in hits} == {"theory:shared", "theory:keyword"}
    assert hits[0].metadata["retrieval"]["degraded_channels"] == ["vector"]
    assert hits[0].metadata["retrieval"]["degraded_reasons"] == {"vector": "RuntimeError"}


@pytest.mark.asyncio
async def test_all_channels_failing_raises_instead_of_returning_empty() -> None:
    """两条通道都挂时必须**显式失败**，不能返回空列表冒充"没有相关内容"。

    这是本仓库反复强调的口径："降级必须可识别，不得将失败静默伪装为成功"。
    调用方据此区分"检索失败"（应重试/告警）与"确实没有命中"（可继续生成结论）。
    """
    search = RrfHybridSearchGateway(
        FailingKeywordSearch(), FailingEmbedding(), LocalVectorStore(), rrf_k=60
    )
    with pytest.raises(RuntimeError, match="均不可用"):
        await search.search(
            RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
        )


@pytest.mark.asyncio
async def test_no_hits_is_not_a_failure() -> None:
    """"无结果"与"故障"是两件事：无命中应正常返回空列表，且不得标记降级。"""
    search = RrfHybridSearchGateway(
        EmptyKeywordSearch(), LocalHashEmbedder(dim=4, model_id="test-model"),
        LocalVectorStore(), rrf_k=60,
    )
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert hits == []


@pytest.mark.asyncio
async def test_rerank_not_configured_does_not_break_retrieval() -> None:
    """故障注入（缺失能力）：Rerank 未接入时检索必须照常可用，且元数据如实只声明 rrf。

    第三期设计里 Rerank 是**可选**项，且当前 PAMI 未提供已验证接口
    （`list /user/api/v1/model/list?modelType=rerank` 实测 0 个模型）。
    所以这里要锁的是"没有它也能出结果"，而不是"它会降级"。
    """
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    vec, other = await embedding.embed(["目标", "别的"])
    await vector.upsert(
        "theory",
        [
            VectorRecord(id="vector", vector=vec, text="向量命中"),
            VectorRecord(id="other", vector=other, text="其它"),
        ],
        model=embedding.model_id,
    )
    search = RrfHybridSearchGateway(FakeKeywordSearch(), embedding, vector, rrf_k=60)
    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert hits, "Rerank 缺失不应导致没有结果"
    assert hits[0].metadata["retrieval"]["algorithm"] == "rrf"
    assert hits[0].metadata["retrieval"]["degraded_channels"] == []


@pytest.mark.asyncio
async def test_authority_drop_is_reported_instead_of_silently_empty() -> None:
    """命中被权威回填丢光时，必须**可识别**，不能只回一个空列表（D13）。

    这是本仓库真实的踩坑：权威表 `retrieval_document` 为空时，回填把**每一条**命中
    都判为"非权威"丢掉，于是线上检索对任何问题都返回空——而它与"确实没有命中"
    完全同形（`degraded=False`、审计与探针都看不出）。真实报告里 `sources` 为空就是
    这么来的。

    这里用一个"全部丢光"的 authority 锁住两条信号：审计 `degraded=True`，
    以及有幸存命中时 metadata 里的丢弃条数。
    """
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    seeded, = await embedding.embed(["目标"])
    await vector.upsert(
        "theory",
        [VectorRecord(id="doc-1", vector=seeded, text="命中")],
        model=embedding.model_id,
    )

    class DroppingAuthority:
        async def hydrate(self, request, hits):  # noqa: ANN001, ANN201
            from zhiyin_infrastructure.persistence.retrieval_documents import (
                HydrationOutcome,
            )

            return HydrationOutcome(hits=[], checked=len(hits), dropped=len(hits))

    spy = AuditSpy()
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), embedding, vector, rrf_k=60, audit=spy
    )
    search.configure_authority(DroppingAuthority())

    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert hits == [], "权威门挡掉后结果为空（策略不变）"
    assert spy.last_degraded is True, "空了但**不能**静默：审计必须标记降级"
    assert spy.last_reason == "authority_drop", (
        "审计必须说清**是哪种降级**（通道故障 vs 被权威门丢），否则运维只能反推"
    )


@pytest.mark.asyncio
async def test_authority_partial_drop_is_recorded_on_surviving_hits() -> None:
    """部分被挡掉时，幸存命中要带上丢弃条数，便于回答"这次是不是少了很多证据"。"""
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()
    seeded, = await embedding.embed(["目标"])
    await vector.upsert(
        "theory",
        [VectorRecord(id="doc-1", vector=seeded, text="命中")],
        model=embedding.model_id,
    )

    class HalfAuthority:
        async def hydrate(self, request, hits):  # noqa: ANN001, ANN201
            from zhiyin_infrastructure.persistence.retrieval_documents import (
                HydrationOutcome,
            )

            kept = list(hits)[:1]
            return HydrationOutcome(
                hits=kept, checked=len(hits), dropped=len(hits) - len(kept)
            )

    spy = AuditSpy()
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), embedding, vector, rrf_k=60, audit=spy
    )
    search.configure_authority(HalfAuthority())

    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert hits, "应至少保留一条"
    assert hits[0].metadata["retrieval"]["dropped_non_authoritative"] == 2
    assert spy.last_degraded is True


@pytest.mark.asyncio
async def test_no_drop_keeps_audit_not_degraded() -> None:
    """反向用例：没有命中被挡掉时，审计**不得**被标成降级（避免"到处都降级"而失效）。"""
    embedding = LocalHashEmbedder(dim=4, model_id="test-model")
    vector = LocalVectorStore()

    class KeepingAuthority:
        async def hydrate(self, request, hits):  # noqa: ANN001, ANN201
            from zhiyin_infrastructure.persistence.retrieval_documents import (
                HydrationOutcome,
            )

            return HydrationOutcome(hits=list(hits), checked=len(hits), dropped=0)

    spy = AuditSpy()
    search = RrfHybridSearchGateway(
        FakeKeywordSearch(), embedding, vector, rrf_k=60, audit=spy
    )
    search.configure_authority(KeepingAuthority())

    hits = await search.search(
        RetrievalQuery(query="目标", namespace=RetrievalNamespace.THEORY, top_k=3)
    )
    assert hits, "关键词通道有命中"
    assert spy.last_degraded is False
    assert spy.last_reason == "", "没降级就不该写原因"
    assert "dropped_non_authoritative" not in hits[0].metadata["retrieval"]


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
