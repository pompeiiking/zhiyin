"""检索文档权威存储与向量命中回填。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Sequence

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery

from .database import _sync_url
from .models import RetrievalDocumentRow


@dataclass(frozen=True)
class HydrationOutcome:
    """一次权威回填的结果，**含被丢弃的条数**（D13）。

    为什么要把"丢了多少"带出来：回填会把权威库里找不到、或已被过滤的命中整条丢掉。
    权威表为空时，**每一条**命中都会被丢掉，于是调用方拿到一个空列表——而它与
    "确实没有命中"完全同形（`degraded=False`、审计与探针都看不出）。这正是
    《AGENTS.md》§5/§10 说的"静默降级"，所以回填必须把丢弃量交出去。

    没有做成"在 store 上记一个 last_dropped 属性"：容器里同一个 store 被并发请求
    共享，那样读到的可能是别人那一次的丢弃数（串味）。
    """

    hits: list[RetrievalEvidence] = field(default_factory=list)
    checked: int = 0
    """参与回填的命中条数。"""

    dropped: int = 0
    """命中存在、但权威库里找不到或对其不可见，因而被丢弃的条数。"""

    @property
    def all_dropped(self) -> bool:
        return bool(self.checked) and self.dropped == self.checked


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
    ) -> HydrationOutcome:
        """权威回填：只保留权威库里存在且对该用户可见的命中。

        返回 `HydrationOutcome`（含丢弃条数），而不是裸列表——见该数据类的说明。
        """
        return await asyncio.to_thread(self._hydrate_sync, request, list(hits))

    def _hydrate_sync(
        self, request: RetrievalQuery, hits: list[RetrievalEvidence]
    ) -> HydrationOutcome:
        if not hits:
            return HydrationOutcome()
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
        dropped = 0
        for hit in hits:
            row = by_key.get(hit.evidence_id) or by_key.get(hit.source_id)
            if row is None or not self._visible(row, request, now):
                dropped += 1
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
        return HydrationOutcome(hits=hydrated, checked=len(hits), dropped=dropped)

    def expire_due(self, *, now: datetime | None = None) -> list[str]:
        """把**已过截止时间**的文档落成 `expired`，并标记为历史样本。

        为什么必须落状态，而不只是靠 `_visible()` 在查询时过滤：
        `_visible()` 确实已经让过期文档检不出来，但记录本身仍是 `enabled`——
        于是"待审 / 禁用 / 过期内容不能进入生产索引"这条**在索引侧不成立**
        （向量库仍会保留它），报表与审计也看不出它已过期，只剩"查不到"这一个现象。

        口径见《第三期 RAG 检索内容与检索流程设计》§4.3：
        「JD 默认是高时效内容。已过截止时间…必须标记 `expired`，不得作为"现在可以申请"
        的证据；历史 JD 可保留用于要求分析，但要明确标记为历史样本。」
        所以这里同时写 `historical_sample=True`——**保留可分析，但永不作为在招证据**。

        只处理 `status == "enabled"` 的行：`disabled` / `pending_review` 本就不该在索引里，
        `expired` 重复扫也无意义（幂等：第二次调用返回空列表）。
        时间比较在 Python 侧做，与 `_visible()` 用同一套时区归一化，避免驱动差异。
        """
        moment = now or datetime.now(timezone.utc)
        expired: list[str] = []
        with self._sessions() as session:
            rows = session.scalars(
                select(RetrievalDocumentRow).where(
                    RetrievalDocumentRow.status == "enabled",
                    RetrievalDocumentRow.expire_at.is_not(None),
                )
            ).all()
            for row in rows:
                expires = row.expire_at
                if expires is None:
                    continue
                if expires.replace(tzinfo=expires.tzinfo or timezone.utc) > moment:
                    continue
                self._mark_expired(row, moment, reason="past_deadline")
                expired.append(row.id)
            session.commit()
        return expired

    def expire_by_source(
        self,
        source_id: str,
        *,
        reason: str = "source_removed",
        now: datetime | None = None,
    ) -> list[str]:
        """**来源下架**：把该来源仍在用的文档整体标记为 `expired`。

        与"到点过期"分开是因为触发方不同——这一条由采集/治理流程在**来源下架**时调用
        （来源台账里的 `removal_method` 就是按 `source_id` 下架），而不是等时间到期。
        """
        moment = now or datetime.now(timezone.utc)
        expired: list[str] = []
        with self._sessions() as session:
            rows = session.scalars(
                select(RetrievalDocumentRow).where(
                    RetrievalDocumentRow.status == "enabled",
                    RetrievalDocumentRow.source_id == source_id,
                )
            ).all()
            for row in rows:
                self._mark_expired(row, moment, reason=reason)
                expired.append(row.id)
            session.commit()
        return expired

    @staticmethod
    def _mark_expired(row: RetrievalDocumentRow, moment: datetime, *, reason: str) -> None:
        """统一的过期落状态：状态 + 原因 + 历史样本标记。

        原因写进 `metadata_json` 而不是新开一列：过期原因是**审计线索**，
        不是检索维度，不值得为它改表结构（也就不会牵动迁移）。
        """
        row.status = "expired"
        row.metadata_json = {
            **(row.metadata_json or {}),
            "expired_reason": reason,
            "expired_at": moment.isoformat(),
            "historical_sample": True,
        }
        row.updated_at = moment

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
