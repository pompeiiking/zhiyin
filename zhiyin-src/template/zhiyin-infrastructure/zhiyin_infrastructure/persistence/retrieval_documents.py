"""检索文档权威存储与向量命中回填。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Sequence

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery

from .database import _sync_url
from .models import RetrievalDocumentRow


class RetrievalDocumentStore:
    """MySQL/SQLite 权威文档存储；不暴露为新的跨层能力位。"""

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(_sync_url(database_url), pool_pre_ping=True, future=True)
        self._sessions = sessionmaker(bind=self._engine, expire_on_commit=False, future=True)

    def upsert(
        self,
        *,
        document_id: str,
        namespace: RetrievalNamespace,
        source_id: str,
        content: str,
        version: int = 1,
        title: str = "",
        source_url: str = "",
        org_id: str = "",
        user_id: str = "",
        status: str = "enabled",
        metadata: dict[str, Any] | None = None,
        effective_at: datetime | None = None,
        expire_at: datetime | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._sessions() as session:
            row = session.get(RetrievalDocumentRow, document_id)
            values = {
                "namespace": namespace.value,
                "source_id": source_id,
                "content": content,
                "version": version,
                "title": title,
                "source_url": source_url,
                "org_id": org_id,
                "user_id": user_id,
                "status": status,
                "metadata_json": metadata or {},
                "effective_at": effective_at,
                "expire_at": expire_at,
                "content_hash": sha256(content.encode("utf-8")).hexdigest(),
                "updated_at": now,
            }
            if row is None:
                row = RetrievalDocumentRow(id=document_id, created_at=now, **values)
                session.add(row)
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            session.commit()

    async def hydrate(
        self, request: RetrievalQuery, hits: Sequence[RetrievalEvidence]
    ) -> list[RetrievalEvidence]:
        return await asyncio.to_thread(self._hydrate_sync, request, list(hits))

    def _hydrate_sync(
        self, request: RetrievalQuery, hits: list[RetrievalEvidence]
    ) -> list[RetrievalEvidence]:
        if not hits:
            return []
        ids = {hit.evidence_id for hit in hits} | {
            hit.source_id for hit in hits if hit.source_id
        }
        now = datetime.now(timezone.utc)
        with self._sessions() as session:
            rows = session.scalars(
                select(RetrievalDocumentRow).where(
                    RetrievalDocumentRow.namespace == request.namespace.value,
                    (RetrievalDocumentRow.id.in_(ids))
                    | (RetrievalDocumentRow.source_id.in_(ids)),
                )
            ).all()
        by_key = {row.id: row for row in rows}
        by_key.update({row.source_id: row for row in rows})
        hydrated: list[RetrievalEvidence] = []
        for hit in hits:
            row = by_key.get(hit.evidence_id) or by_key.get(hit.source_id)
            if row is None or not self._visible(row, request, now):
                continue
            hydrated.append(
                hit.model_copy(
                    update={
                        "evidence_id": row.id,
                        "source_id": row.source_id,
                        "content": row.content,
                        "title": row.title,
                        "source_url": row.source_url,
                        "version": row.version,
                        "updated_at": row.updated_at,
                        "metadata": {**row.metadata_json, **hit.metadata},
                    }
                )
            )
        return hydrated

    @staticmethod
    def _visible(row: RetrievalDocumentRow, request: RetrievalQuery, now: datetime) -> bool:
        if row.status != "enabled":
            return False
        effective = row.effective_at
        expires = row.expire_at
        if effective is not None and effective.replace(tzinfo=effective.tzinfo or timezone.utc) > now:
            return False
        if expires is not None and expires.replace(tzinfo=expires.tzinfo or timezone.utc) <= now:
            return False
        if row.org_id and row.org_id != request.org_id:
            return False
        if row.user_id and row.user_id != request.user_id:
            return False
        return True

    def close(self) -> None:
        self._engine.dispose()


__all__ = ["RetrievalDocumentStore"]
