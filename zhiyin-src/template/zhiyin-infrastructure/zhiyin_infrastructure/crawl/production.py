"""可独立部署的 M3 生产采集执行器。"""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal
from uuid import uuid4

from zhiyin_infrastructure.crawl.pipeline import (
    CrawlReport,
    Fetcher,
    KnowledgeIngestionPipeline,
    KnowledgeSource,
)

CrawlMode = Literal["full", "incremental", "scheduled", "manual"]
AlertSink = Callable[[dict[str, Any]], None | Awaitable[None]]


class CrawlPausedError(RuntimeError):
    """页面结构或数据契约变化，来源已暂停等待人工检查。"""


@dataclass
class ProductionCrawlRunner:
    """逐阶段重试、持久化状态并在结构变化时熔断写入。"""

    pipeline: KnowledgeIngestionPipeline
    state_dir: Path
    alert: AlertSink | None = None
    max_attempts: int = 3

    async def run(
        self,
        source: KnowledgeSource,
        fetcher: Fetcher,
        *,
        mode: CrawlMode = "incremental",
        job_id: str | None = None,
    ) -> CrawlReport:
        self.pipeline._ensure_allowed(source)
        job_id = job_id or f"crawl_job_{uuid4().hex[:16]}"
        trace_id = f"trace_{uuid4().hex[:16]}"
        batch_id = f"crawl_{uuid4().hex[:12]}"
        self._write_state(job_id, source, mode, "running", "fetch", trace_id)
        try:
            raw = await self._retry("fetch", lambda: fetcher(source), job_id, source, mode, trace_id)
            await self._retry(
                "raw_cache",
                lambda: self.pipeline._cache_raw(source, batch_id, trace_id, raw),
                job_id,
                source,
                mode,
                trace_id,
            )
            items = await self._retry(
                "parse", lambda: self.pipeline._parse(raw), job_id, source, mode, trace_id
            )
            fetched_at = datetime.now(timezone.utc)
            normalized = await self._retry(
                "normalize",
                lambda: [
                    self.pipeline._normalize(source, item, fetched_at, batch_id, trace_id)
                    for item in items
                ],
                job_id,
                source,
                mode,
                trace_id,
            )
            reviewed = []
            for item in normalized:
                reviewed.append(
                    await self._retry(
                        "review",
                        lambda current=item: self.pipeline._review(source, current),
                        job_id,
                        source,
                        mode,
                        trace_id,
                    )
                )
            stored, unchanged, published = await self._retry(
                "store",
                lambda: self.pipeline._store(source.namespace, reviewed),
                job_id,
                source,
                mode,
                trace_id,
            )
            if published and self.pipeline.on_index_updated is not None:
                await self._retry(
                    "index",
                    lambda: self.pipeline.on_index_updated(source.namespace),
                    job_id,
                    source,
                    mode,
                    trace_id,
                )
            report = CrawlReport(
                source_id=source.source_id,
                namespace=source.namespace,
                batch_id=batch_id,
                trace_id=trace_id,
                fetched=len(items),
                stored=stored,
                unchanged=unchanged,
                pending_review=sum(item["review_status"] == "pending_review" for item in reviewed),
                rejected=sum(item["review_status"] == "rejected" for item in reviewed),
                fetched_at=fetched_at,
                content_hashes=[item["content_hash"] for item in normalized],
            )
            self._write_state(
                job_id, source, mode, "completed", "done", trace_id, report=report.model_dump(mode="json")
            )
            return report
        except (ValueError, KeyError, TypeError) as exc:
            await self._pause(job_id, source, mode, trace_id, exc)
            raise CrawlPausedError(f"来源 {source.source_id} 结构变化，已暂停写入") from exc
        except Exception as exc:
            self._write_state(job_id, source, mode, "failed", "failed", trace_id, error=str(exc))
            raise

    async def _retry(
        self,
        stage: str,
        operation: Callable[[], Any | Awaitable[Any]],
        job_id: str,
        source: KnowledgeSource,
        mode: CrawlMode,
        trace_id: str,
    ) -> Any:
        for attempt in range(1, self.max_attempts + 1):
            self._write_state(job_id, source, mode, "running", stage, trace_id, attempt=attempt)
            try:
                result = operation()
                return await result if inspect.isawaitable(result) else result
            except (ValueError, KeyError, TypeError):
                raise
            except Exception:
                if attempt >= self.max_attempts:
                    raise
                await asyncio.sleep(min(2 ** (attempt - 1), 10))
        raise AssertionError("unreachable")

    async def _pause(
        self,
        job_id: str,
        source: KnowledgeSource,
        mode: CrawlMode,
        trace_id: str,
        error: Exception,
    ) -> None:
        event = {
            "type": "crawl_source_paused",
            "source_id": source.source_id,
            "trace_id": trace_id,
            "reason": str(error),
        }
        self._write_state(job_id, source, mode, "paused", "quality_check", trace_id, error=str(error))
        if self.alert is not None:
            result = self.alert(event)
            if inspect.isawaitable(result):
                await result

    def _write_state(
        self,
        job_id: str,
        source: KnowledgeSource,
        mode: CrawlMode,
        status: str,
        stage: str,
        trace_id: str,
        **extra: Any,
    ) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "job_id": job_id,
            "source_id": source.source_id,
            "namespace": source.namespace,
            "mode": mode,
            "status": status,
            "stage": stage,
            "trace_id": trace_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        path = self.state_dir / f"{job_id}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)


__all__ = ["CrawlMode", "CrawlPausedError", "ProductionCrawlRunner"]
