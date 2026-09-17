"""在 Docker 网络中验证 M3 四类真实基础设施适配器。

该脚本只写入带随机后缀的探针数据，并在退出前清理，不依赖 pytest。
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from zhiyin_data_sdk.gateways.vector import VectorRecord
from zhiyin_infrastructure.minio import MinioObjectStore
from zhiyin_infrastructure.mysql import (
    DatabaseContext,
    SqlAlchemyRawQueryGateway,
    build_repository_set,
)
from zhiyin_infrastructure.persistence.database import SqlAlchemyTransactionManager
from zhiyin_infrastructure.pgvector import PgVectorGateway
from zhiyin_infrastructure.redis import RedisClientFactory
from zhiyin_kernel.blackboard import ProfileField
from zhiyin_kernel.enums import ProfileSource


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少运行验证配置：{name}")
    return value


async def _verify_mysql(probe: str) -> None:
    database_url = _required("ZHIYIN_DATABASE_URL")
    context = DatabaseContext(database_url)
    repositories = build_repository_set(context)
    raw_query = SqlAlchemyRawQueryGateway(database_url)
    transactions = SqlAlchemyTransactionManager(database_url)
    user_id = f"verify-{probe}"
    try:
        stored = await repositories["profiles"].upsert_field(
            user_id,
            ProfileField(
                key="runtime_probe",
                value="ok",
                confidence=1.0,
                source=ProfileSource.CONVERSATION,
                updated_at=datetime.now(timezone.utc),
                evidence=["m3-runtime-verifier"],
            ),
        )
        assert stored.key == "runtime_probe"
        profile = await repositories["profiles"].get(user_id)
        assert profile is not None and profile.user_id == user_id
        count = await raw_query.fetch_one(
            "SELECT COUNT(*) AS count FROM profile WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        assert count == {"count": 1}
        with transactions.begin() as transaction:
            assert transaction.session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        async with context.engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM profile WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
        await raw_query.close()
        transactions.close()
        await context.close()


async def _verify_redis(probe: str) -> None:
    factory = RedisClientFactory(
        _required("ZHIYIN_REDIS_URL"),
        password=_required("ZHIYIN_REDIS_PASSWORD"),
    )
    store = factory.domain_store("verify", "test")
    try:
        await store.set_json("runtime", probe, {"status": "ok"}, ttl_s=60)
        assert await store.get_json("runtime", probe) == {"status": "ok"}
    finally:
        await store.delete("runtime", probe)
        await factory.close()


async def _verify_pgvector(probe: str) -> None:
    gateway = PgVectorGateway(_required("ZHIYIN_VECTOR_DATABASE_URL"))
    vector = [0.0] * 1024
    vector[0] = 1.0
    try:
        written = await gateway.upsert(
            "theory",
            [
                VectorRecord(
                    id=probe,
                    vector=vector,
                    text="M3 runtime probe",
                    source_id=probe,
                    metadata={"probe": True},
                )
            ],
            model="runtime-probe-v1",
        )
        assert written == 1
        hits = await gateway.search(
            "theory",
            vector,
            model="runtime-probe-v1",
            top_k=1,
            filters={"probe": True},
        )
        assert hits and hits[0].id == probe
        pool = await gateway._get_pool()
        async with pool.acquire() as connection, connection.transaction():
            await connection.execute("SET LOCAL enable_seqscan = off")
            plan_rows = await connection.fetch(
                """
                EXPLAIN SELECT record_id
                FROM zhiyin_vectors
                ORDER BY embedding <=> $1
                LIMIT 1
                """,
                vector,
            )
        plan = "\n".join(str(row[0]) for row in plan_rows)
        assert "ix_zhiyin_vectors_hnsw" in plan, plan
        print("pgvector_query_plan=hnsw")
    finally:
        await gateway.delete("theory", [probe])
        await gateway.close()


async def _verify_minio(probe: str) -> None:
    store = MinioObjectStore(
        _required("ZHIYIN_MINIO_ENDPOINT"),
        _required("ZHIYIN_MINIO_ACCESS_KEY"),
        _required("ZHIYIN_MINIO_SECRET_KEY"),
        secure=False,
    )
    key = f"runtime-verify/{probe}.txt"
    try:
        first = await store.put(key, b"m3-ok", content_type="text/plain")
        assert await store.get(key) == b"m3-ok"
        second = await store.compare_and_swap(
            key,
            b"m3-updated",
            expected_etag=first.etag,
            content_type="text/plain",
        )
        assert second is not None
        assert await store.get(key) == b"m3-updated"
    finally:
        await store.delete(key)


async def main() -> None:
    probe = uuid4().hex
    checks = {
        "mysql_repository": _verify_mysql,
        "redis_adapter": _verify_redis,
        "pgvector_gateway": _verify_pgvector,
        "minio_gateway": _verify_minio,
    }
    for name, check in checks.items():
        await check(probe)
        print(f"{name}=ok")


if __name__ == "__main__":
    asyncio.run(main())
