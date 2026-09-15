"""第一期合规采集最小链路：Fetch → Parse → Normalize → Store → Index。

网络访问由调用方注入 ``fetcher``。管线自身不会绕过登录、验证码、robots 或站点
限制；只有来源台账明确标记为 enabled 且 allowed 的来源才能执行。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

Fetcher = Callable[["KnowledgeSource"], Any | Awaitable[Any]]


class KnowledgeSource(BaseModel):
    """来源台账中的一项授权记录。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    name: str
    source_url: str
    namespace: str
    acquisition: Literal["open_api", "open_data", "allowed_page", "manual_import"]
    allowed: bool = False
    allowed_scope: str
    owner: str
    refresh_interval: str
    removal_method: str
    retention: str
    status: Literal["enabled", "disabled", "pending_review"] = "pending_review"
    removal_key: str = "source_id"


class CrawlReport(BaseModel):
    """一次采集批次的可追溯结果。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    namespace: str
    batch_id: str
    trace_id: str
    fetched: int = 0
    stored: int = 0
    unchanged: int = 0
    fetched_at: datetime
    content_hashes: list[str] = Field(default_factory=list)


@dataclass
class KnowledgeIngestionPipeline:
    """只处理获准来源，并将规范化结果幂等写入本地知识库。"""

    knowledge_dir: Path
    on_index_updated: Callable[[str], None] | None = None
    raw_store: Any | None = None
    raw_ttl_s: int = 3_600

    async def run(
        self,
        source: KnowledgeSource,
        fetcher: Fetcher,
        *,
        trace_id: str | None = None,
    ) -> CrawlReport:
        self._ensure_allowed(source)
        self._namespace_path(source.namespace)
        batch_id = f"crawl_{uuid4().hex[:12]}"
        trace_id = trace_id or f"trace_{uuid4().hex[:16]}"
        raw = fetcher(source)
        if inspect.isawaitable(raw):
            raw = await raw
        await self._cache_raw(source, batch_id, trace_id, raw)
        items = self._parse(raw)
        fetched_at = datetime.now(timezone.utc)
        normalized = [
            self._normalize(source, item, fetched_at, batch_id, trace_id)
            for item in items
        ]
        stored, unchanged = self._store(source.namespace, normalized)
        if stored and self.on_index_updated is not None:
            self.on_index_updated(source.namespace)
        return CrawlReport(
            source_id=source.source_id,
            namespace=source.namespace,
            batch_id=batch_id,
            trace_id=trace_id,
            fetched=len(items),
            stored=stored,
            unchanged=unchanged,
            fetched_at=fetched_at,
            content_hashes=[item["content_hash"] for item in normalized],
        )

    def disable_source(self, namespace: str, source_id: str) -> int:
        """按来源下架已入库条目，保留记录并标记 disabled。"""
        path = self._namespace_path(namespace)
        payload = self._load_payload(path)
        changed = 0
        for item in payload["items"]:
            if item.get("source_id") == source_id and item.get("status") != "disabled":
                item["status"] = "disabled"
                changed += 1
        if changed:
            self._write_payload(path, payload)
            if self.on_index_updated is not None:
                self.on_index_updated(namespace)
        return changed

    def disable_item(
        self,
        namespace: str,
        source_id: str,
        source_item_id: str,
        *,
        version: int | None = None,
    ) -> int:
        """按来源唯一键（可选限定版本）精确下架条目。"""
        path = self._namespace_path(namespace)
        payload = self._load_payload(path)
        changed = 0
        for item in payload["items"]:
            matched = (
                item.get("source_id") == source_id
                and item.get("source_item_id", item.get("id")) == source_item_id
                and (version is None or int(item.get("version", 0)) == version)
            )
            if matched and item.get("status") != "disabled":
                item["status"] = "disabled"
                changed += 1
        if changed:
            self._write_payload(path, payload)
            if self.on_index_updated is not None:
                self.on_index_updated(namespace)
        return changed

    def remove_source(self, namespace: str, source_id: str) -> int:
        """按来源物理删除本地演示数据；调用方须先完成授权/保留期判断。"""
        path = self._namespace_path(namespace)
        payload = self._load_payload(path)
        before = len(payload["items"])
        payload["items"] = [
            item for item in payload["items"] if item.get("source_id") != source_id
        ]
        removed = before - len(payload["items"])
        if removed:
            self._write_payload(path, payload)
            if self.on_index_updated is not None:
                self.on_index_updated(namespace)
        return removed

    @staticmethod
    def load_sources(path: str | Path) -> list[KnowledgeSource]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return [KnowledgeSource.model_validate(item) for item in raw.get("items", [])]

    @staticmethod
    def _ensure_allowed(source: KnowledgeSource) -> None:
        if not source.allowed or source.status != "enabled":
            raise PermissionError(f"知识来源未获准采集：{source.source_id}")
        if not source.allowed_scope.strip():
            raise PermissionError(f"知识来源缺少允许范围：{source.source_id}")
        if not source.source_url.strip():
            raise PermissionError(f"知识来源缺少来源地址：{source.source_id}")
        required = {
            "owner": source.owner,
            "refresh_interval": source.refresh_interval,
            "removal_method": source.removal_method,
            "retention": source.retention,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise PermissionError(
                f"知识来源登记不完整：{source.source_id}，缺少 {', '.join(missing)}"
            )

    @staticmethod
    def _parse(raw: Any) -> list[dict[str, Any]]:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            raw = json.loads(raw)
        if isinstance(raw, dict):
            raw = raw.get("items", [])
        if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
            raise ValueError("第一期采集器只接受 JSON 对象数组或包含 items 的 JSON 对象")
        return list(raw)

    @staticmethod
    def _normalize(
        source: KnowledgeSource,
        raw: dict[str, Any],
        fetched_at: datetime,
        batch_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        item = dict(raw)
        identifier = str(item.get("id") or item.get("occupation_code") or item.get("major_code") or "").strip()
        title = str(item.get("title") or item.get("name") or "").strip()
        if not identifier or not title:
            raise ValueError("知识条目必须包含稳定 id/编码和 title/name")
        # 来源唯一键必须包含 source_id；不同来源使用同一个站内 id 时不得覆盖。
        item["source_item_id"] = identifier
        item["id"] = f"{source.source_id}:{identifier}"
        item["title"] = title
        item["namespace"] = source.namespace
        item["source_id"] = source.source_id
        item["source"] = source.name
        item["source_url"] = source.source_url
        item["fetched_at"] = fetched_at.isoformat()
        item["batch_id"] = batch_id
        item["trace_id"] = trace_id
        item["review_status"] = "approved"
        item["status"] = "enabled"
        for field in ("city", "education", "experience"):
            if field in item:
                item[field] = " ".join(str(item[field]).split())
        if "skills" in item:
            skills = item["skills"]
            if isinstance(skills, str):
                skills = re.split(r"[,，、;；]", skills)
            if not isinstance(skills, list):
                raise ValueError("skills 必须是字符串或字符串数组")
            item["skills"] = list(
                dict.fromkeys(str(skill).strip() for skill in skills if str(skill).strip())
            )
        canonical = json.dumps(
            {
                key: value
                for key, value in item.items()
                if key
                not in {
                    "fetched_at",
                    "version",
                    "content_hash",
                    "status",
                    "batch_id",
                    "trace_id",
                }
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        item["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return item

    async def _cache_raw(
        self,
        source: KnowledgeSource,
        batch_id: str,
        trace_id: str,
        raw: Any,
    ) -> None:
        if self.raw_store is None:
            return
        if self.raw_ttl_s <= 0:
            raise ValueError("采集原始响应缓存必须设置正数 TTL")
        if isinstance(raw, bytes):
            payload = raw.decode("utf-8")
        elif isinstance(raw, str):
            payload = raw
        else:
            payload = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        await self.raw_store.set_json(
            "raw",
            batch_id,
            {
                "source_id": source.source_id,
                "trace_id": trace_id,
                "payload": payload,
            },
            ttl_s=self.raw_ttl_s,
        )

    def _store(self, namespace: str, incoming: list[dict[str, Any]]) -> tuple[int, int]:
        path = self._namespace_path(namespace)
        payload = self._load_payload(path)
        by_id = {str(item.get("id")): item for item in payload["items"]}
        stored = 0
        unchanged = 0
        for item in incoming:
            current = by_id.get(item["id"])
            if current is not None and current.get("content_hash") == item["content_hash"]:
                item["version"] = int(current.get("version", 1))
                item["fetched_at"] = current.get("fetched_at", item["fetched_at"])
                unchanged += 1
            else:
                item["version"] = int(current.get("version", 0)) + 1 if current else 1
                stored += 1
            by_id[item["id"]] = item
        payload["items"] = sorted(by_id.values(), key=lambda item: str(item.get("id", "")))
        self._write_payload(path, payload)
        return stored, unchanged

    def _namespace_path(self, namespace: str) -> Path:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", namespace):
            raise ValueError(f"非法知识命名空间：{namespace}")
        root = self.knowledge_dir.resolve()
        path = (root / f"{namespace}.json").resolve()
        if root not in path.parents:
            raise ValueError(f"知识命名空间越出存储目录：{namespace}")
        return path

    @staticmethod
    def _load_payload(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {"_note": "由第一期合规采集最小链路生成", "items": []}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return {"items": raw}
        if not isinstance(raw, dict) or not isinstance(raw.get("items", []), list):
            raise ValueError(f"知识文件格式无效：{path}")
        return raw

    @staticmethod
    def _write_payload(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)


__all__ = ["CrawlReport", "KnowledgeIngestionPipeline", "KnowledgeSource"]
