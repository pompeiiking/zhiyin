"""Arbeitnow 公开岗位 API 的最小采集实验。

目标是验证 Fetch -> Parse -> Normalize -> Deduplicate -> Snapshot，而不是建设生产爬虫。
只访问公开、无需登录的 JSON API；不提交申请、不处理候选人数据、不绕过访问控制。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

DEFAULT_URL = "https://www.arbeitnow.com/api/job-board-api"
SOURCE_ID = "arbeitnow-public-api"
USER_AGENT = "ZhiyinDataExperiment/0.1 (+https://github.com/pompeiiking/zhiyin)"
EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def html_to_text(value: str) -> str:
    """将岗位描述转换成稳定的纯文本，避免在知识库里保存可执行 HTML。"""
    parser = _TextExtractor()
    parser.feed(html.unescape(value or ""))
    parser.close()
    return " ".join(parser.parts)


def redact_contacts(value: str) -> str:
    """移除描述中的邮箱与长电话号码；联系人姓名不做自动猜测。"""
    value = EMAIL_PATTERN.sub("[redacted-email]", value)
    return PHONE_PATTERN.sub("[redacted-phone]", value)


def fetch_json(url: str = DEFAULT_URL, *, timeout_s: float = 20.0) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_s) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status: {response.status}")
        charset = response.headers.get_content_charset() or "utf-8"
        payload = json.loads(response.read().decode(charset))
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("API response must contain a data array")
    return payload


@dataclass(frozen=True)
class NormalizedJob:
    id: str
    source_id: str
    source_item_id: str
    title: str
    company_name: str
    location: str
    remote: bool
    job_types: list[str]
    tags: list[str]
    description_summary: str
    published_at: str | None
    source_url: str
    fetched_at: str
    content_hash: str


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(" ".join(str(item).split()) for item in value if str(item).strip()))


def _published_at(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def normalize_job(raw: dict[str, Any], *, fetched_at: datetime) -> NormalizedJob:
    slug = str(raw.get("slug") or "").strip()
    title = " ".join(str(raw.get("title") or "").split())
    source_url = str(raw.get("url") or "").strip()
    if not slug or not title or not source_url.startswith("https://"):
        raise ValueError("job requires slug, title and an https source URL")

    stable = {
        "source_item_id": slug,
        "title": title,
        "company_name": " ".join(str(raw.get("company_name") or "").split()),
        "location": " ".join(str(raw.get("location") or "").split()),
        "remote": bool(raw.get("remote")),
        "job_types": _clean_list(raw.get("job_types")),
        "tags": _clean_list(raw.get("tags")),
        # 实验只保留短摘要；原始 HTML 不进入长期存储。
        "description_summary": redact_contacts(
            html_to_text(str(raw.get("description") or ""))
        )[:1200],
        "published_at": _published_at(raw.get("created_at")),
        "source_url": source_url,
    }
    canonical = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return NormalizedJob(
        id=f"{SOURCE_ID}:{slug}",
        source_id=SOURCE_ID,
        fetched_at=fetched_at.isoformat(),
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        **stable,
    )


def normalize_payload(
    payload: dict[str, Any], *, keyword: str = "", limit: int = 20, fetched_at: datetime | None = None
) -> tuple[list[NormalizedJob], int]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    fetched_at = fetched_at or datetime.now(timezone.utc)
    needle = keyword.casefold().strip()
    raw_items = payload.get("data")
    if not isinstance(raw_items, list):
        raise TypeError("payload.data must be an array")

    jobs: list[NormalizedJob] = []
    rejected = 0
    seen: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            rejected += 1
            continue
        haystack = " ".join(
            [
                str(raw.get("title") or ""),
                str(raw.get("company_name") or ""),
                str(raw.get("location") or ""),
                " ".join(map(str, raw.get("tags") or [])),
            ]
        ).casefold()
        if needle and needle not in haystack:
            continue
        try:
            job = normalize_job(raw, fetched_at=fetched_at)
        except (TypeError, ValueError, OverflowError, OSError):
            rejected += 1
            continue
        if job.id in seen:
            continue
        seen.add(job.id)
        jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs, rejected


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def build_snapshot(jobs: Iterable[NormalizedJob], *, rejected: int, api_url: str) -> dict[str, Any]:
    items = [asdict(job) for job in jobs]
    return {
        "_meta": {
            "experiment": "public-job-api-ingestion",
            "source_id": SOURCE_ID,
            "api_url": api_url,
            "stored": len(items),
            "rejected": rejected,
            "raw_response_persisted": False,
            "notice": "实验快照；展示或复用时必须保留 source_url 和来源归属。",
        },
        "items": items,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="离线 JSON 响应；省略时调用公开 API")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--keyword", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        payload = fetch_json(args.url)
    jobs, rejected = normalize_payload(payload, keyword=args.keyword, limit=args.limit)
    snapshot = build_snapshot(jobs, rejected=rejected, api_url=args.url)
    _atomic_write(args.output, snapshot)
    print(json.dumps(snapshot["_meta"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
