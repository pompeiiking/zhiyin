from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from xuezhi_experiment import normalize_major, normalize_occupation


def test_normalize_major_is_traceable_and_stable() -> None:
    item = normalize_major(
        {
            "specId": "spec-1",
            "zydm": "080901",
            "zymc": "计算机科学与技术",
            "cc": "本科（普通教育）",
            "mlmc": "工学",
            "xk": "计算机类",
            "evlValue": 4.1,
            "evlNum": 10,
        },
        fetched_at="2026-09-16T00:00:00+00:00",
    )
    assert item["id"] == "xuezhi-chsi:major:spec-1"
    assert item["major_code"] == "080901"
    assert item["source_url"].endswith("specId=spec-1")
    assert len(item["content_hash"]) == 64


def test_normalize_occupation_strips_html_and_limits_text() -> None:
    item = normalize_occupation(
        {
            "zhiyId": "occ-1",
            "title": "数据分析师",
            "kthzmc": "互联网类",
            "industrymc": "信息技术",
            "occDesc": "<p>分析<strong>数据</strong>并形成结论。</p>",
        },
        fetched_at="2026-09-16T00:00:00+00:00",
    )
    assert item["description_summary"] == "分析 数据 并形成结论。"
    assert "<strong>" not in item["description_summary"]
    assert item["source_url"].endswith("id=occ-1")
