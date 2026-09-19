"""离线检索质量基准 runner（《第三期 RAG 检索内容与检索流程设计》§12）。

为什么需要这个脚本
------------------
`zhiyin_infrastructure/retrieval_evaluation.evaluate_retrieval()` 早就实现了
Recall@K 与 MRR，但**仓库里没有任何调用方**——指标算得出来，却没人跑，
于是"固定评测集达到评审后的质量门槛"这条一直悬着。本脚本把它接到可执行入口上。

用法
----
    python scripts/eval_retrieval.py
    python scripts/eval_retrieval.py --top-k 20 --out /tmp/baseline.json
    python scripts/eval_retrieval.py --knowledge-dir data/knowledge

口径（**读数字前必须先读这段**）
--------------------------------
1. 默认跑的是**本地关键词通道**（读 `data/knowledge/*.json`），不依赖数据库、
   模型与网络，因此任何环境都能跑出可复现的结果。
2. 报告里同时给出 **expected_id 覆盖率**：评测集的 `expected_ids` 由"测试知识快照"
   提供，而**该快照当前不在仓库里**（全仓只有 `data/evaluation/` 下的评测集与
   schema 两个文件）。覆盖率为 0 时 Recall / MRR 必然是 0——**那时这两个数字
   不衡量检索质量**，只说明"评测集与语料没对上"。
3. 因此本脚本的产出是**可复现的基准与诊断**，不是质量结论；门槛必须等真实内容
   进索引、覆盖率上去之后再冻结。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
if str(TEMPLATE_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT))

from zhiyin_infrastructure.local.knowledge import LocalSearchGateway  # noqa: E402
from zhiyin_infrastructure.retrieval_evaluation import evaluate_retrieval  # noqa: E402
from zhiyin_kernel.enums import RetrievalNamespace  # noqa: E402
from zhiyin_kernel.retrieval import RetrievalQuery  # noqa: E402


def corpus_ids(knowledge_dir: Path) -> dict[str, set[str]]:
    """本地语料里每个 namespace 的文档 id，**按通道口径**收集为 `namespace:id`。

    D11 之后 `LocalSearchGateway` 统一返回 `namespace:id`，所以这里也只收集这一种
    形态：如果仍然把裸 id 与带前缀两种都算进来，"覆盖率"就会把**口径不一致**的
    命中当成真命中，反而看不出问题（这正是修 D11 之前那份基准报告的做法）。
    """
    ids: dict[str, set[str]] = defaultdict(set)
    if not knowledge_dir.is_dir():
        return ids
    for path in sorted(knowledge_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else (payload.get("items") or [])
        for item in items:
            raw_id = item.get("id")
            if not raw_id:
                continue
            namespace = str(item.get("namespace") or path.stem)
            ids[namespace].add(f"{namespace}:{raw_id}")
    return ids


async def channel_id_convention(search: LocalSearchGateway, knowledge_dir: Path) -> dict[str, Any]:
    """实测**通道真正返回的** id 形态，而不是从语料文件推断。

    修 D11 之前的脚本是从语料 JSON 推断的，于是"通道会不会加前缀"这件事根本没被
    验证——语料里两种形态都在，它永远报"不一致"。现在直接问通道要一次真实结果。
    """
    probe: dict[str, Any] = {"queried": False, "qualified": None, "sample": []}
    if not knowledge_dir.is_dir():
        return probe
    for path in sorted(knowledge_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else (payload.get("items") or [])
        for item in items:
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            namespace = str(item.get("namespace") or path.stem)
            try:
                namespace_enum = RetrievalNamespace(namespace)
            except ValueError:
                continue
            hits = await search.search(
                RetrievalQuery(query=title, namespace=namespace_enum, top_k=3)
            )
            if not hits:
                continue
            probe["queried"] = True
            probe["sample"] = [hit.evidence_id for hit in hits][:3]
            probe["qualified"] = all(
                hit.evidence_id.startswith(f"{namespace}:") for hit in hits
            )
            return probe
    return probe


def coverage_report(dataset: Path, ids: dict[str, set[str]]) -> dict[str, Any]:
    """期望 id 的覆盖率：有多少条期望能在语料（按通道口径）里找到。"""
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    cases = payload.get("items", [])
    per_namespace: dict[str, dict[str, int]] = defaultdict(
        lambda: {"cases": 0, "expected": 0, "hit": 0}
    )
    total_expected = total_hit = 0
    qualified_expected = 0
    for case in cases:
        namespace = str(case.get("namespace") or "")
        expected = [str(value) for value in case.get("expected_ids", [])]
        bucket = per_namespace[namespace]
        bucket["cases"] += 1
        bucket["expected"] += len(expected)
        present = ids.get(namespace, set())
        hits = sum(1 for item in expected if item in present)
        bucket["hit"] += hits
        total_expected += len(expected)
        total_hit += hits
        if any(":" in item for item in expected):
            qualified_expected += 1
    return {
        "expected_total": total_expected,
        "expected_found": total_hit,
        "coverage": (total_hit / total_expected) if total_expected else 0.0,
        "per_namespace": dict(per_namespace),
        "corpus_ids": {name: len(values) for name, values in ids.items()},
        "expectations_namespace_qualified": qualified_expected == len(cases) and bool(cases),
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    knowledge_dir = Path(args.knowledge_dir)
    search = LocalSearchGateway(str(knowledge_dir))
    metrics = await evaluate_retrieval(search, args.dataset, top_k=args.top_k)
    coverage = coverage_report(Path(args.dataset), corpus_ids(knowledge_dir))
    channel_ids = await channel_id_convention(search, knowledge_dir)
    return {
        "dataset": str(args.dataset),
        "dataset_version": metrics.get("dataset_version"),
        "top_k": args.top_k,
        "channel": "local-keyword",
        "knowledge_dir": str(knowledge_dir),
        "case_count": metrics.get("case_count"),
        "recall_at_k": metrics.get("recall_at_k"),
        "mrr": metrics.get("mrr"),
        "expected_coverage": coverage,
        "channel_ids": channel_ids,
        "usable_as_quality_baseline": coverage["coverage"] > 0.0,
        "note": (
            "expected_coverage 为 0 时，Recall/MRR 恒为 0，**不衡量检索质量**："
            "评测集的期望 id 指向一份不在仓库里的测试知识快照。"
            "门槛须等真实内容进索引、覆盖率上去后再冻结。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="离线检索质量基准")
    parser.add_argument(
        "--dataset",
        default=str(TEMPLATE_ROOT / "data" / "evaluation" / "retrieval_cases.json"),
    )
    parser.add_argument(
        "--knowledge-dir", default=str(TEMPLATE_ROOT / "data" / "knowledge")
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out", default="", help="把完整结果写到该 JSON 文件")
    args = parser.parse_args()

    result = asyncio.run(run(args))
    coverage = result["expected_coverage"]

    print(f"评测集      : {result['dataset']}（{result['dataset_version']}）")
    print(f"通道        : {result['channel']} ← {result['knowledge_dir']}")
    print(f"用例数      : {result['case_count']}   top_k={result['top_k']}")
    print(f"Recall@K    : {result['recall_at_k']:.4f}")
    print(f"MRR         : {result['mrr']:.4f}")
    print(
        f"期望覆盖率  : {coverage['coverage']:.4f}"
        f"（{coverage['expected_found']}/{coverage['expected_total']}）"
    )
    print("  按 namespace:")
    for namespace, bucket in sorted(coverage["per_namespace"].items()):
        print(
            f"    {namespace:<12} 用例 {bucket['cases']:>3}  "
            f"期望命中 {bucket['hit']:>3}/{bucket['expected']:<3}"
        )
    print(f"  语料 id 数  : {coverage['corpus_ids'] or '（空）'}")
    channel_ids = result["channel_ids"]
    if coverage["expectations_namespace_qualified"] and channel_ids.get("qualified") is False:
        print(
            "  id 口径不一致: 评测集期望写 `namespace:id`，而实测通道返回裸 id"
            f"（样例 {channel_ids.get('sample')}）。\n"
            "    这会让「内容明明存在却匹配不上」，也会让关键词通道与向量通道的同一篇"
            "文档在 RRF 融合时被当成两篇（去重键是 evidence_id）。"
        )
    elif channel_ids.get("qualified"):
        print(
            f"  id 口径一致  : 通道实测返回 `namespace:id`（样例 {channel_ids.get('sample')}）。"
        )
    if not result["usable_as_quality_baseline"]:
        print(f"\n[注意] {result['note']}")
    if args.out:
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n完整结果已写入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
