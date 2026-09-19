"""脱敏检索元数据记录与保留期清理。"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete

from zhiyin_infrastructure.mysql.repositories import DatabaseContext
from zhiyin_infrastructure.persistence.models import RetrievalLogRow


class RetrievalLogStore:
    """只保存查询哈希和命中来源，不保存查询原文。"""

    def __init__(self, context: DatabaseContext, *, retention_days: int = 180) -> None:
        self._db = context
        self._retention_days = retention_days

    async def record(
        self,
        *,
        org_id: str,
        namespace: str,
        channel: str,
        top_k: int,
        source_ids: list[str],
        latency_ms: int,
        degraded: bool,
        query: str,
        degraded_reason: str = "",
    ) -> None:
        await self._db.ensure_ready()
        async with self._db.sessions.begin() as session:
            session.add(
                RetrievalLogRow(
                    id=f"ret_{uuid4().hex}",
                    org_id=org_id,
                    namespace=namespace,
                    channel=channel,
                    top_k=top_k,
                    source_ids=source_ids,
                    latency_ms=latency_ms,
                    degraded=degraded,
                    degraded_reason=degraded_reason[:32],
                    query_hash=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    created_at=datetime.now(timezone.utc),
                )
            )

    async def purge_expired(self) -> int:
        await self._db.ensure_ready()
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        async with self._db.sessions.begin() as session:
            result = await session.execute(
                delete(RetrievalLogRow).where(RetrievalLogRow.created_at < cutoff)
            )
            return max(int(result.rowcount or 0), 0)


__all__ = ["RetrievalLogStore"]
