"""PostgreSQL + pgvector 的 :class:`VectorGateway` 实现。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Optional

from zhiyin_data_sdk.errors import UnavailableError, ValidationError
from zhiyin_data_sdk.gateways.vector import VectorGateway, VectorHit, VectorRecord

VECTOR_DIMENSION = 1024
NAMESPACES = frozenset({"theory", "occupation", "jd", "report", "memory", "resume"})


def _dsn(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("postgresql+asyncpg://"):
        cleaned = "postgresql://" + cleaned.removeprefix("postgresql+asyncpg://")
    if not cleaned.startswith(("postgresql://", "postgres://")):
        raise ValueError("pgvector 数据库地址必须是 PostgreSQL DSN")
    return cleaned


def _validate_namespace(namespace: str) -> None:
    if namespace not in NAMESPACES:
        raise ValidationError(
            "未知向量命名空间",
            detail={"namespace": namespace, "allowed": sorted(NAMESPACES)},
        )


def _validate_vector(vector: Sequence[float]) -> list[float]:
    if len(vector) != VECTOR_DIMENSION:
        raise ValidationError(
            "向量维度必须为 1024",
            detail={"actual_dimension": len(vector)},
        )
    return [float(value) for value in vector]


def _decode_metadata(value: Any) -> dict[str, Any]:
    """兼容 asyncpg 默认 JSONB codec（字符串）与测试连接池（字典）。"""
    if value is None:
        return {}
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, dict):
        raise ValueError("pgvector metadata 必须是 JSON 对象")
    return dict(decoded)


class PgVectorGateway(VectorGateway):
    """使用单表、命名空间和模型版本隔离的 pgvector 实现。

    表与 HNSW 索引由部署迁移创建；适配器使用最小权限账号，仅做 DML。
    ``pool`` 参数只用于契约测试和由平台统一管理连接池的场景。
    """

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        database_url: str,
        *,
        pool: Any | None = None,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ) -> None:
        self._database_url = _dsn(database_url)
        self._pool = pool
        self._owns_pool = pool is None
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size

    async def _get_pool(self) -> Any:
        if self._pool is not None:
            return self._pool
        try:
            import asyncpg
            from pgvector.asyncpg import register_vector

            async def initialize(connection: Any) -> None:
                await register_vector(connection)

            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
                init=initialize,
            )
        except Exception as exc:
            raise UnavailableError("无法连接 pgvector", cause=exc) from exc
        return self._pool

    async def close(self) -> None:
        if self._owns_pool and self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def upsert(
        self, namespace: str, records: Sequence[VectorRecord], *, model: str
    ) -> int:
        _validate_namespace(namespace)
        if not model.strip():
            raise ValidationError("向量模型标识不能为空")
        if not records:
            return 0
        rows = [
            (
                namespace,
                record.id,
                model,
                _validate_vector(record.vector),
                record.text,
                record.source_id,
                json.dumps(record.metadata, ensure_ascii=False),
            )
            for record in records
        ]
        sql = """
            INSERT INTO zhiyin_vectors
                (namespace, record_id, model, embedding, text, source_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            ON CONFLICT (namespace, record_id, model) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                text = EXCLUDED.text,
                source_id = EXCLUDED.source_id,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
        """
        try:
            pool = await self._get_pool()
            await pool.executemany(sql, rows)
        except Exception as exc:
            if isinstance(exc, (UnavailableError, ValidationError)):
                raise
            raise UnavailableError("pgvector 写入失败", cause=exc) from exc
        return len(rows)

    async def search(
        self,
        namespace: str,
        vector: Sequence[float],
        *,
        model: str,
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[VectorHit]:
        _validate_namespace(namespace)
        normalized = _validate_vector(vector)
        if not model.strip():
            raise ValidationError("向量模型标识不能为空")
        if top_k <= 0:
            return []
        sql = """
            SELECT record_id, text, source_id, metadata,
                   1 - (embedding <=> $3) AS score
            FROM zhiyin_vectors
            WHERE namespace = $1 AND model = $2
              AND ($4::jsonb IS NULL OR metadata @> $4::jsonb)
            ORDER BY embedding <=> $3
            LIMIT $5
        """
        filter_json = json.dumps(filters, ensure_ascii=False) if filters else None
        try:
            pool = await self._get_pool()
            rows = await pool.fetch(
                sql, namespace, model, normalized, filter_json, min(top_k, 100)
            )
        except Exception as exc:
            if isinstance(exc, (UnavailableError, ValidationError)):
                raise
            raise UnavailableError("pgvector 检索失败", cause=exc) from exc
        return [
            VectorHit(
                id=str(row["record_id"]),
                score=float(row["score"]),
                text=str(row["text"] or ""),
                source_id=str(row["source_id"] or ""),
                metadata=_decode_metadata(row["metadata"]),
            )
            for row in rows
        ]

    async def delete(self, namespace: str, ids: Sequence[str]) -> int:
        _validate_namespace(namespace)
        if not ids:
            return 0
        try:
            pool = await self._get_pool()
            result = await pool.execute(
                "DELETE FROM zhiyin_vectors WHERE namespace = $1 AND record_id = ANY($2)",
                namespace,
                list(ids),
            )
        except Exception as exc:
            if isinstance(exc, (UnavailableError, ValidationError)):
                raise
            raise UnavailableError("pgvector 删除失败", cause=exc) from exc
        return int(str(result).rsplit(" ", 1)[-1])

    async def clear_namespace(self, namespace: str) -> None:
        _validate_namespace(namespace)
        try:
            pool = await self._get_pool()
            await pool.execute("DELETE FROM zhiyin_vectors WHERE namespace = $1", namespace)
        except Exception as exc:
            if isinstance(exc, (UnavailableError, ValidationError)):
                raise
            raise UnavailableError("pgvector 清空命名空间失败", cause=exc) from exc


__all__ = ["NAMESPACES", "VECTOR_DIMENSION", "PgVectorGateway"]
