"""经 PAMI 的真实检索质量基准（自检索冒烟，供冻结门槛参考）。

它测什么、不测什么（**读数字前必读**）
--------------------------------------
- **测**：用真实平台（PAMI RAG，含真实 embedding 与 rerank）检索我们导入的 22 份
  自有内容时，**目标文档是否被召回、排在第几**。这回答"召回链路是否真的可用、
  排序是否合理"。
- **不测**：真实用户问法的检索质量。用例是**机械化生成**的——查询直接取自文档自身
  的标题/名称，所以它天然偏乐观，**不能**当成"用户随便问也能召回"的结论，也不该
  单独用来冻结面向用户的质量门槛。

为什么按"标题"而不是 id 判定命中：平台检索响应只回 `kb_name/title/snippet`
（没有文档 id、没有 score，见修改日志 §25.5）。好在我们导入时把**文件名**放进了
平台文档标题，而文件名与语料 id 一一对应，所以可以按文件名判定。

与 `scripts/eval_retrieval.py` 的关系：那个跑的是**冻结的 100 条评测集 + 本地关键词
通道**（期望覆盖率恒为 0，数字不是质量结论）；本脚本跑的是**真实平台 + 机械用例**，
两者互补，不可互相替代。

用法::

    python scripts/eval_pami_retrieval.py                    # 22 份文档，top_k=5
    python scripts/eval_pami_retrieval.py --top-k 10 --out r.json

密钥只从 gitignored 的 `deploy/.env` 读，只打印长度。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
from dataclasses import dataclass

TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(TEMPLATE_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT))

from zhiyin_infrastructure.pami.adapters import PamiSearchGateway  # noqa: E402
from zhiyin_kernel.enums import RetrievalNamespace  # noqa: E402
from zhiyin_kernel.retrieval import RetrievalQuery  # noqa: E402


@dataclass(frozen=True)
class Case:
    case_id: str
    query: str
    expected_title: str
    namespace: str


def _read_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_cases() -> list[Case]:
    """按导入时的命名规则机械还原 22 份文档及其查询。

    命名规则来自导入脚本（`rag_step3.py` 的同一套约定）：
    - registry 理论卡 → `theory_card_<id>.txt`
    - 语料切片        → `<namespace>_<id>.txt`
    """
    cases: list[Case] = []

    cards = json.loads(
        (TEMPLATE_ROOT / "data/registry/theory_cards.json").read_text(encoding="utf-8")
    )
    for card in cards["items"]:
        cases.append(
            Case(
                case_id=f"card:{card['id']}",
                query=str(card["name"]),
                expected_title=f"theory_card_{card['id']}.txt",
                namespace="theory",
            )
        )

    for namespace, relative in (
        ("theory", "data/knowledge/theory.json"),
        ("occupation", "data/knowledge/occupation.json"),
    ):
        payload = json.loads((TEMPLATE_ROOT / relative).read_text(encoding="utf-8"))
        for item in payload.get("items") or []:
            cases.append(
                Case(
                    case_id=f"{namespace}:{item['id']}",
                    query=str(item.get("title") or item["id"]),
                    expected_title=f"{namespace}_{item['id']}.txt",
                    namespace=namespace,
                )
            )
    return cases


async def run(args: argparse.Namespace) -> dict:
    env_file = _read_env_file(pathlib.Path(args.env_file))
    import os

    key = os.environ.get("ZHIYIN_PAMI_RAG_API_KEY") or env_file.get(
        "ZHIYIN_PAMI_RAG_API_KEY", ""
    )
    # ⚠️ **不要**默认用 .env 里的 `ZHIYIN_PAMI_BASE_URL`：那是**容器内**地址
    # （`http://nginx:8081`），在宿主机上解析不了 `nginx`。踩过一次：22 个用例全部
    # `UnavailableError`，而报告差点显示成"Recall@5 = 0.0000"这种像质量结论的数字。
    # 本脚本是宿主机工具，默认走 nginx 的宿主端口；要跑在容器里就显式传 --pami-base-url。
    base_url = (
        args.pami_base_url
        or os.environ.get("ZHIYIN_PAMI_HOST_URL")
        or "http://127.0.0.1:8081"
    )
    print(f"平台        : {base_url}")
    print(f"RAG Key     : {'已配置，长度 ' + str(len(key)) if key else '缺失'}")
    if not key:
        raise SystemExit("缺少 RAG Key（deploy/.env 的 ZHIYIN_PAMI_RAG_API_KEY）")

    search = PamiSearchGateway(base_url, key, timeout_s=90.0)
    cases = build_cases()
    print(f"用例数      : {len(cases)}（由导入命名规则机械生成）  top_k={args.top_k}")

    hits_total = 0
    reciprocal_ranks: list[float] = []
    details: list[dict] = []
    for index, case in enumerate(cases, start=1):
        query = RetrievalQuery(
            query=case.query,
            namespace=RetrievalNamespace(case.namespace),
            top_k=args.top_k,
            mode="keyword",
        )
        try:
            hits = await search.search(query)
        except Exception as exc:  # noqa: BLE001 - 单例失败不该中断整轮基准
            print(f"  [{index:>2}/{len(cases)}] {case.case_id} 检索失败 {type(exc).__name__}")
            details.append({"case": case.case_id, "hit": False, "rank": None, "error": type(exc).__name__})
            reciprocal_ranks.append(0.0)
            continue
        titles = [hit.title for hit in hits]
        rank = next(
            (position for position, title in enumerate(titles, start=1)
             if title == case.expected_title),
            None,
        )
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        hits_total += len(hits)
        details.append(
            {"case": case.case_id, "query": case.query, "expected": case.expected_title,
             "hit": rank is not None, "rank": rank, "titles": titles}
        )
        mark = "✅" if rank else "❌"
        print(f"  [{index:>2}/{len(cases)}] {mark} rank={rank} {case.query[:18]!r} "
              f"→ {titles[:2]}")

    found = sum(1 for item in details if item["hit"])
    result = {
        "channel": "pami-rag (real platform)",
        "case_count": len(cases),
        "top_k": args.top_k,
        "recall_at_k": found / len(cases) if cases else 0.0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "returned_hits": hits_total,
        "note": (
            "机械化自检索用例（查询取自文档自身标题）：衡量召回链路是否可用与排序是否合理，"
            "偏乐观，**不能**单独用来冻结面向用户的质量门槛。"
            "平台不返回文档 id/score，故按标题（文件名）判定命中。"
        ),
        "details": details,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="经 PAMI 的真实检索质量基准")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--env-file", default=str(TEMPLATE_ROOT / "deploy" / ".env"))
    parser.add_argument("--pami-base-url", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    result = asyncio.run(run(args))
    print("\n== 结果 ==")
    print(f"Recall@{result['top_k']} : {result['recall_at_k']:.4f}"
          f"（{int(result['recall_at_k'] * result['case_count'])}/{result['case_count']}）")
    print(f"MRR        : {result['mrr']:.4f}")
    print(f"召回条目总数: {result['returned_hits']}")
    print(f"[注意] {result['note']}")
    if args.out:
        pathlib.Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"完整结果已写入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
