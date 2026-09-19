"""学职平台公开页面的数据入口发现实验。

仅访问无需登录的专业洞察/职业探索入口及其同源静态脚本，识别公开接口候选；
不登录、不提交表单、不调用个性化推荐或测评接口、不绕过访问控制。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE_URL = "https://xz.chsi.com.cn"
DEFAULT_PAGES = (
    f"{BASE_URL}/speciality/index.action",
    f"{BASE_URL}/occupation/index.action",
)
USER_AGENT = "ZhiyinDataExperiment/0.1 (+https://github.com/pompeiiking/zhiyin)"
ENDPOINT_PATTERN = re.compile(
    r"(?P<quote>['\"])(?P<url>(?:https?://xz\.chsi\.com\.cn)?/[^'\"\s]{1,240}"
    r"(?:\.action|\.json)(?:\?[^'\"\s]{0,240})?)(?P=quote)"
)
MAJOR_LIST_URL = f"{BASE_URL}/speciality/list.action"
OCCUPATION_LIST_URL = f"{BASE_URL}/occupation/searchbyhy.action"


@dataclass
class PageDiscovery:
    url: str
    status: int
    content_type: str
    meta_robots: str | None = None
    script_urls: list[str] = field(default_factory=list)
    endpoint_candidates: list[str] = field(default_factory=list)


class _PageParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__()
        self.page_url = page_url
        self.meta_robots: str | None = None
        self.script_urls: list[str] = []
        self.inline_scripts: list[str] = []
        self._inside_script = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and str(values.get("name", "")).casefold() == "robots":
            self.meta_robots = values.get("content")
        if tag == "script":
            source = values.get("src")
            if source:
                self.script_urls.append(urljoin(self.page_url, source))
            else:
                self._inside_script = True
                self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._inside_script:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inside_script:
            self.inline_scripts.append("".join(self._script_parts))
            self._inside_script = False
            self._script_parts = []


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def fetch_text(url: str, *, timeout_s: float = 30.0, max_bytes: int = 3_000_000) -> tuple[int, str, str]:
    request = Request(url, headers={"Accept": "text/html,*/*", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_s) as response:
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError(f"response exceeds {max_bytes} bytes: {url}")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.status, str(response.headers.get("Content-Type", "")), payload.decode(
            charset, errors="replace"
        )


def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    from urllib.parse import urlencode

    target = f"{url}?{urlencode(params)}"
    _, _, text = fetch_text(target)
    payload = json.loads(text.strip())
    if not isinstance(payload, dict) or payload.get("flag") is not True:
        raise ValueError(f"public endpoint returned an unsuccessful payload: {url}")
    return payload


def html_to_text(value: str) -> str:
    parser = _TextParser()
    parser.feed(html.unescape(value or ""))
    parser.close()
    return " ".join(parser.parts)


def _hash(item: dict[str, Any]) -> str:
    canonical = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_major(raw: dict[str, Any], *, fetched_at: str) -> dict[str, Any]:
    spec_id = str(raw.get("specId") or "").strip()
    major_code = str(raw.get("zydm") or "").strip()
    name = str(raw.get("zymc") or "").strip()
    if not spec_id or not major_code or not name:
        raise ValueError("major requires specId, zydm and zymc")
    stable = {
        "source_id": "xuezhi-chsi",
        "source_item_id": spec_id,
        "major_code": major_code,
        "name": name,
        "education_level": str(raw.get("cc") or "").strip(),
        "discipline": str(raw.get("mlmc") or "").strip(),
        "category": str(raw.get("xk") or "").strip(),
        "satisfaction_rating": raw.get("evlValue"),
        "rating_count": raw.get("evlNum"),
        "source_url": f"{BASE_URL}/speciality/detail.action?specId={spec_id}",
    }
    return {
        "id": f"xuezhi-chsi:major:{spec_id}",
        **stable,
        "fetched_at": fetched_at,
        "content_hash": _hash(stable),
    }


def normalize_occupation(raw: dict[str, Any], *, fetched_at: str) -> dict[str, Any]:
    occupation_id = str(raw.get("zhiyId") or "").strip()
    title = str(raw.get("title") or "").strip()
    if not occupation_id or not title:
        raise ValueError("occupation requires zhiyId and title")
    stable = {
        "source_id": "xuezhi-chsi",
        "source_item_id": occupation_id,
        "title": title,
        "category": str(raw.get("kthzmc") or "").strip(),
        "industry": str(raw.get("industrymc") or "").strip(),
        "description_summary": html_to_text(str(raw.get("occDesc") or ""))[:800],
        "source_url": f"{BASE_URL}/occupation/occudetail.action?id={occupation_id}",
    }
    return {
        "id": f"xuezhi-chsi:occupation:{occupation_id}",
        **stable,
        "fetched_at": fetched_at,
        "content_hash": _hash(stable),
    }


def fetch_public_samples(limit: int = 5) -> dict[str, Any]:
    if not 1 <= limit <= 15:
        raise ValueError("sample limit must be between 1 and 15")
    fetched_at = datetime.now(timezone.utc).isoformat()
    major_payload = fetch_json(
        MAJOR_LIST_URL,
        {"start": 0, "phbType": 1, "cc": "", "ml": "", "xk": "", "zymc": ""},
    )
    occupation_payload = fetch_json(
        OCCUPATION_LIST_URL,
        {
            "industryId": "",
            "ktId": "",
            "name": "",
            "start": 0,
            "curPage": 1,
            "pageCount": 10,
            "totalCount": 0,
        },
    )
    major_data = major_payload.get("data") or {}
    occupation_data = occupation_payload.get("data") or {}
    majors = [
        normalize_major(item, fetched_at=fetched_at)
        for item in list(major_data.get("pageArray") or [])[:limit]
    ]
    occupations = [
        normalize_occupation(item, fetched_at=fetched_at)
        for item in list(occupation_data.get("zhiyArray") or [])[:limit]
    ]
    return {
        "counts_reported_by_source": {
            "majors": int(major_data.get("totalCount") or 0),
            "occupations": int(occupation_data.get("totalCount") or 0),
        },
        "majors": majors,
        "occupations": occupations,
    }


def _same_origin_asset(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc == "xz.chsi.com.cn"


def _endpoint_candidates(text: str) -> set[str]:
    return {urljoin(BASE_URL, match.group("url")) for match in ENDPOINT_PATTERN.finditer(text)}


def discover_page(url: str, *, inspect_scripts: bool = True) -> PageDiscovery:
    status, content_type, html = fetch_text(url)
    parser = _PageParser(url)
    parser.feed(html)
    candidates = _endpoint_candidates(html)
    candidates.update(_endpoint_candidates("\n".join(parser.inline_scripts)))

    script_urls = sorted(set(filter(_same_origin_asset, parser.script_urls)))
    if inspect_scripts:
        for script_url in script_urls:
            try:
                _, _, script = fetch_text(script_url)
            except (OSError, TimeoutError, ValueError):
                continue
            candidates.update(_endpoint_candidates(script))

    # 登录、测评、收藏、个性化推荐不属于本实验允许范围，发现后也不输出为采集候选。
    denied_fragments = ("login", "survey", "collect", "recommend", "account")
    safe_candidates = sorted(
        candidate
        for candidate in candidates
        if not any(fragment in candidate.casefold() for fragment in denied_fragments)
    )
    return PageDiscovery(
        url=url,
        status=status,
        content_type=content_type,
        meta_robots=parser.meta_robots,
        script_urls=script_urls,
        endpoint_candidates=safe_candidates,
    )


def build_report(pages: list[PageDiscovery], samples: dict[str, Any]) -> dict[str, Any]:
    return {
        "_meta": {
            "experiment": "xuezhi-public-entry-discovery",
            "source_id": "xuezhi-chsi",
            "base_url": BASE_URL,
            "pages_checked": len(pages),
            "login_used": False,
            "forms_submitted": False,
            "raw_pages_persisted": False,
            "result": "public_sample_collected_pending_access_review",
            "records_stored": len(samples["majors"]) + len(samples["occupations"]),
        },
        "pages": [page.__dict__ for page in pages],
        "samples": samples,
    }


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-script-scan", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pages = [discover_page(url, inspect_scripts=not args.no_script_scan) for url in DEFAULT_PAGES]
    samples = fetch_public_samples(args.limit)
    report = build_report(pages, samples)
    atomic_write(args.output, report)
    print(json.dumps(report["_meta"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
