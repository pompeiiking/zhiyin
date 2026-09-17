"""向量同步任务表的并发安全队列。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from zhiyin_infrastructure.mysql.repositories import DatabaseContext
from zhiyin_infrastructure.persistence.models import EmbedTaskRow


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class EmbedTask:
    id: str
    namespace: str
    source_id: str
    model: str
    content_hash: str
    text: str
    metadata: dict[str, Any]
    operation: str
    attempts: int


class EmbedTaskStore:
    """使用行锁领取任务，保证多个独立 Worker 不会重复处理同一任务。"""

    def __init__(self, context: DatabaseContext, *, max_attempts: int = 5) -> None:
        self._db = context
        self._max_attempts = max_attempts

    async def enqueue(
        self,
        *,
        namespace: str,
        source_id: str,
        model: str,
        content_hash: str,
        text: str = "",
        metadata: dict[str, Any] | None = None,
        operation: str = "upsert",
    ) -> str:
        if operation not in {"upsert", "delete"}:
            raise ValueError("operation 只能是 upsert 或 delete")
        await self._db.ensure_ready()
        now = _now()
        async with self._db.sessions.begin() as session:
            existing = await session.scalar(
                select(EmbedTaskRow).where(
                    EmbedTaskRow.namespace == namespace,
                    EmbedTaskRow.source_id == source_id,
                    EmbedTaskRow.model == model,
                    EmbedTaskRow.content_hash == content_hash,
                    EmbedTaskRow.operation == operation,
                )
            )
            if existing is not None:
                if existing.status in {"failed", "done"}:
                    existing.status = "pending"
                    existing.attempts = 0
                    existing.next_retry_at = None
                    existing.last_error = ""
                    existing.updated_at = now
                return existing.id
            task_id = f"emb_{uuid4().hex}"
            session.add(
                EmbedTaskRow(
                    id=task_id,
                    namespace=namespace,
                    source_id=source_id,
                    model=model,
                    content_hash=content_hash,
                    text=text,
                    metadata_json=metadata or {},
                    operation=operation,
                    status="pending",
                    attempts=0,
                    next_retry_at=None,
                    last_error="",
                    created_at=now,
                    updated_at=now,
                )
            )
            return task_id

    async def claim(self, *, limit: int = 50) -> list[EmbedTask]:
        await self._db.ensure_ready()
        now = _now()
        async with self._db.sessions.begin() as session:
            statement = (
                select(EmbedTaskRow)
                .where(
                    EmbedTaskRow.status.in_(("pending", "retry")),
                    EmbedTaskRow.attempts < self._max_attempts,
                    (EmbedTaskRow.next_retry_at.is_(None))
                    | (EmbedTaskRow.next_retry_at <= now),
                )
                .order_by(EmbedTaskRow.created_at, EmbedTaskRow.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            rows = list((await session.scalars(statement)).all())
            for row in rows:
                row.status = "running"
                row.attempts += 1
                row.updated_at = now
            return [
                EmbedTask(
                    id=row.id,
                    namespace=row.namespace,
                    source_id=row.source_id,
                    model=row.model,
                    content_hash=row.content_hash,
                    text=row.text,
                    metadata=dict(row.metadata_json),
                    operation=row.operation,
                    attempts=row.attempts,
                )
                for row in rows
            ]

    async def succeed(self, task_id: str) -> None:
        await self._set_result(task_id, status="done")

    async def fail(self, task_id: str, error: Exception) -> None:
        await self._db.ensure_ready()
        now = _now()
        async with self._db.sessions.begin() as session:
            row = await session.get(EmbedTaskRow, task_id, with_for_update=True)
            if row is None:
                return
            row.status = "failed" if row.attempts >= self._max_attempts else "retry"
            row.next_retry_at = now + timedelta(seconds=min(300, 2 ** row.attempts))
            row.last_error = str(error)[:1000]
            row.updated_at = now

    async def _set_result(self, task_id: str, *, status: str) -> None:
        await self._db.ensure_ready()
        async with self._db.sessions.begin() as session:
            row = await session.get(EmbedTaskRow, task_id, with_for_update=True)
            if row is not None:
                row.status = status
                row.next_retry_at = None
                row.last_error = ""
                row.updated_at = _now()


__all__ = ["EmbedTask", "EmbedTaskStore"]
