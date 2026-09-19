"""把职引自有内容载入**权威文档表**与向量队列（D7 ③ 的最后一步）。

为什么需要它
------------
`retrieval_document` 是检索的**权威来源**：`RrfHybridSearchGateway` 返回前会调
`RetrievalDocumentStore.hydrate()`，命中在该表里找不到就**整条丢弃**。而这表此前
**没有任何生产方**（只有测试和装配代码引用它），于是线上所有命中都被丢掉——审计里
表现为 `degraded=1, 命中=0`（D13 已把这件事变得可见）。

后果是双向的：
- 模型拿不到任何检索上下文（答案只能靠猜）；
- 引用溯源无从谈起（没有权威行就没有版本、没有出处）。

本脚本补上这条链路：内容 → 权威表 + 向量队列（`embed_task`，由 `vector_sync`
Worker 消费）。**它不生产内容，只把已有内容登记进权威存储。**

内容与 id 口径
--------------
内容取自项目自有文件（与导入平台时的同一份）：

- `data/registry/theory_cards.json`（16 张理论卡）→ `theory:<card_id>`
- `data/knowledge/theory.json`、`data/knowledge/occupation.json` → `<namespace>:<id>`

**演示标记照搬**：这三份文件自述含 DEMO，所以写入权威行时带 `demo=True`。
这很关键——D12 的护栏靠权威行里的 `demo` 维持（`hydrate` 以
`{**row.metadata_json, **hit.metadata}` 合并，命中侧不会覆盖它），
因此演示内容**仍然不会被报告引用**。等真实内容替换后，同样不会带 demo 标记，
届时引用链路会自然生效。

用法::

    python scripts/load_retrieval_documents.py                 # 只打印计划（默认）
    python scripts/load_retrieval_documents.py --apply          # 写权威表 + 入向量队列
    python scripts/load_retrieval_documents.py --apply --no-vectors

需要 `ZHIYIN_DATABASE_URL`（权威表）与向量队列所需的同一个库；密钥不入日志。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any

TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(TEMPLATE_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT))

from zhiyin_infrastructure.persistence.retrieval_documents import (  # noqa: E402
    RetrievalDocumentStore,
)
from zhiyin_kernel.enums import RetrievalNamespace  # noqa: E402


@dataclass(frozen=True)
class CorpusDoc:
    """一份待登记进权威表的内容。"""

    namespace: str
    doc_id: str
    title: str
    content: str
    is_theory_card: bool = False
    source_id: str = ""
    source_url: str = ""
    source: str = ""
    demo: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def document_id(self) -> str:
        """权威表主键，与检索命中的 `evidence_id` 同形（`namespace:id`）。"""
        return f"{self.namespace}:{self.doc_id}"

    @property
    def doc_name(self) -> str:
        """平台侧文档名（与 `pami.doc_naming` 的约定一致）。"""
        marker = "card_" if self.is_theory_card else ""
        return f"{self.namespace}_{marker}{self.doc_id}.txt"


def _load_json(relative: str) -> dict[str, Any]:
    return json.loads((TEMPLATE_ROOT / relative).read_text(encoding="utf-8"))


def _demo_of(payload: dict[str, Any]) -> bool:
    note = str(payload.get("_note") or "")
    return ("DEMO" in note.upper()) or ("演示" in note)


def build_corpus() -> list[CorpusDoc]:
    """把项目自有内容整理成待登记清单（与导入平台时的内容一致）。"""
    docs: list[CorpusDoc] = []

    cards = _load_json("data/registry/theory_cards.json")
    card_demo = _demo_of(cards)
    for card in cards.get("items") or []:
        content = "\n".join(
            part
            for part in (
                f"理论卡：{card.get('name') or card['id']}",
                f"所属流派：{card.get('school') or ''}",
                "通俗说明：",
                str(card.get("summary") or ""),
                "在职引里的用法：",
                str(card.get("product_usage") or ""),
            )
            if part is not None
        )
        docs.append(
            CorpusDoc(
                namespace=RetrievalNamespace.THEORY.value,
                doc_id=str(card["id"]),
                title=str(card.get("name") or card["id"]),
                content=content,
                is_theory_card=True,
                source_id=str(card["id"]),
                demo=card_demo,
                raw=card,
            )
        )

    for relative in ("data/knowledge/theory.json", "data/knowledge/occupation.json"):
        payload = _load_json(relative)
        namespace = str(payload.get("items", [{}])[0].get("namespace") or "") or (
            "theory" if "theory" in relative else "occupation"
        )
        demo = _demo_of(payload)
        for item in payload.get("items") or []:
            body = [
                f"标题：{item.get('title') or item['id']}",
                f"标签：{'、'.join(item.get('tags') or [])}",
                f"来源：{item.get('source') or ''}",
                "",
                str(item.get("summary") or ""),
            ]
            docs.append(
                CorpusDoc(
                    namespace=str(item.get("namespace") or namespace),
                    doc_id=str(item["id"]),
                    title=str(item.get("title") or item["id"]),
                    content="\n".join(body),
                    source_id=str(item.get("source_id") or item["id"]),
                    source_url=str(item.get("source_url") or ""),
                    source=str(item.get("source") or ""),
                    demo=demo,
                    raw=item,
                )
            )
    return docs


async def apply_documents(
    docs: list[CorpusDoc], *, with_vectors: bool, database_url: str, model: str
) -> tuple[int, int]:
    """写权威表；可选把文档放进向量同步队列（由 `vector_sync` Worker 消费）。"""
    from zhiyin_infrastructure.mysql.repositories import DatabaseContext
    from zhiyin_infrastructure.persistence.embed_tasks import EmbedTaskStore
    from zhiyin_infrastructure.workers.vector_sync import VectorSyncPlanner

    store = RetrievalDocumentStore(database_url)
    written = queued = 0
    try:
        for doc in docs:
            store.upsert(
                document_id=doc.document_id,
                namespace=RetrievalNamespace(doc.namespace),
                # ⚠️ 权威表的唯一键是 `(namespace, source_id, version)`，这里的
                # `source_id` 是**文档身份**，不是"来源台账 id"。踩过一次：语料里三个
                # theory 条目的 `source_id` 都是 `src-theory-demo`（同一份来源台账），
                # 直接拿来当文档身份会撞唯一键（IntegrityError）。
                # 台账 id 改放 metadata，保留来源可查性。
                source_id=doc.doc_id,
                content=doc.content,
                version=int(doc.raw.get("version") or 1),
                title=doc.title,
                source_url=doc.source_url,
                status="enabled",
                metadata={
                    # `demo` 必须留在权威行里：D12 的护栏靠它维持
                    "demo": doc.demo,
                    "doc_name": doc.doc_name,
                    "doc_kind": "theory_card" if doc.is_theory_card else "doc",
                    "source": doc.source,
                    "source_ledger_id": doc.source_id,
                    "label": "权威表登记（内容仍为演示数据）" if doc.demo else "权威表登记",
                },
            )
            written += 1

        if with_vectors:
            # `DatabaseContext` 需要 database_url（它自己转成异步 DSN）；不复用外部
            # engine，避免又传又建的重复连接（这里不需要额外配置）。
            context = DatabaseContext(database_url)
            try:
                planner = VectorSyncPlanner(
                    EmbedTaskStore(context), vector=None, model=model  # type: ignore[arg-type]
                )
                for namespace in sorted({doc.namespace for doc in docs}):
                    payload = [
                        {
                            "id": doc.doc_id,
                            "title": doc.title,
                            "content": doc.content,
                            # 向量侧同样用**文档身份**做 source_id，与权威表一致
                            "source_id": doc.doc_id,
                            "source_url": doc.source_url,
                            "version": int(doc.raw.get("version") or 1),
                            # 检索计划会给查询带 `filters={"status": "enabled"}`，
                            # 向量行里没有 status 就会被 `metadata @> filters` 全部过滤掉
                            "status": "enabled",
                            "user_id": "",
                            "org_id": "",
                        }
                        for doc in docs
                        if doc.namespace == namespace
                    ]
                    queued += await planner.schedule_incremental(namespace, payload)
            finally:
                await context.engine.dispose()
    finally:
        store.close()
    return written, queued


def main() -> int:
    parser = argparse.ArgumentParser(description="把自有内容登记进权威表与向量队列")
    parser.add_argument("--apply", action="store_true", help="真正写入（默认只打印计划）")
    parser.add_argument("--no-vectors", action="store_true", help="只写权威表，不入向量队列")
    args = parser.parse_args()

    import os

    database_url = os.environ.get("ZHIYIN_DATABASE_URL", "").strip()
    model = os.environ.get("ZHIYIN_PAMI_EMBEDDING_MODEL_ID", "").strip() or "unknown"

    docs = build_corpus()
    demo_count = sum(1 for doc in docs if doc.demo)
    print(f"待登记 {len(docs)} 份（其中演示内容 {demo_count} 份）")
    print(f"权威表主键形如 : {docs[0].document_id}")
    print(f"平台文档名形如 : {docs[0].doc_name}")
    print(f"向量模型        : {model}")
    for doc in docs[:3]:
        print(f"  {doc.document_id:<44} title={doc.title[:20]!r} demo={doc.demo}")

    if not args.apply:
        print("\n[计划模式] 未写入任何数据；确认后加 --apply")
        return 0
    if not database_url:
        print("缺少 ZHIYIN_DATABASE_URL，无法写入", file=sys.stderr)
        return 2

    written, queued = asyncio.run(
        apply_documents(
            docs,
            with_vectors=not args.no_vectors,
            database_url=database_url,
            model=model,
        )
    )
    print(f"\n已写入权威表 {written} 行；入向量队列 {queued} 条")
    print("提示：向量由 vector_sync Worker 异步写入；可跑 "
          "`python -m zhiyin_boot worker vector_sync --once` 立即处理一轮。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
