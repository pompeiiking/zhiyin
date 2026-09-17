"""固定查询集的检索质量评测。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zhiyin_data_sdk.gateways.ai import SearchGateway


async def evaluate_retrieval(
    search: SearchGateway, dataset: str | Path, *, top_k: int = 10
) -> dict[str, Any]:
    payload = json.loads(Path(dataset).read_text(encoding="utf-8"))
    cases = payload.get("items", [])
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    details: list[dict[str, Any]] = []
    for case in cases:
        expected = {str(value) for value in case.get("expected_ids", [])}
        hits = await search.hybrid(str(case["query"]), top_k=top_k)
        actual = [hit.id for hit in hits]
        matched = expected.intersection(actual)
        recall = len(matched) / len(expected) if expected else 1.0
        first_rank = next((index for index, item_id in enumerate(actual, 1) if item_id in expected), 0)
        recalls.append(recall)
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)
        details.append(
            {
                "namespace": case["namespace"],
                "query": case["query"],
                "actual_ids": actual,
                "recall": recall,
                "reciprocal_rank": reciprocal_ranks[-1],
            }
        )
    count = len(cases)
    return {
        "dataset_version": payload.get("version", "unknown"),
        "case_count": count,
        "recall_at_k": sum(recalls) / count if count else 0.0,
        "mrr": sum(reciprocal_ranks) / count if count else 0.0,
        "details": details,
    }


__all__ = ["evaluate_retrieval"]
