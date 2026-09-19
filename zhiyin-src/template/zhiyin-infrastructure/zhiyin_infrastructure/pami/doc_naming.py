"""平台文档命名约定：让"平台回传的标题"能还原成职引的文档 id（D7 ③ 的回填口径）。

为什么需要它
------------
平台的检索响应只有 `kb_name / title / snippet`——**不回文档 id**（见修改日志 §25.5）。
而职引的引用溯源与权威回填都需要来源 id：

- `Report.source_versions` 按来源取版本；
- `RetrievalDocumentStore.hydrate()` 要拿命中去权威表里找得到对应行，否则**整条命中被丢弃**。

所以导入平台时的**文件名**必须能反解出 `(namespace, id)`。本模块把这条约定写在一处，
**导入侧与检索侧共用**，避免两边各写一份正则而慢慢漂移。

约定（两种形态，都从文件名反解）
--------------------------------
1. 普通文档：``<namespace>_<id>.txt``      —— 例：``theory_theory-clover.txt`` → theory / theory-clover
2. 理论卡：  ``<namespace>_card_<id>.txt`` —— 例：``theory_card_holland_riasec.txt`` → theory / holland_riasec

反解规则：以**第一个下划线**切出 namespace（必须是已知 namespace），剩下部分若以
`card_` 开头则视为理论卡、其后的整体是 id（因此 id 里的下划线会被完整保留）。

为什么按这个规则而不是更"聪明"的推断：它只有一步切分、可判定、且 namespace 必须在
已知集合内——不满足就返回 `None`，由调用方回落到内容哈希（而不是猜出一个错的 id，
那会让权威回填静默失配）。
"""

from __future__ import annotations

from dataclasses import dataclass

from zhiyin_kernel.enums import RetrievalNamespace

#: 理论卡文件名里的标记段
CARD_MARKER = "card"

_NAMESPACES = {item.value for item in RetrievalNamespace}


@dataclass(frozen=True)
class ParsedDocName:
    """从平台文档名反解出的职引文档身份。"""

    namespace: str
    doc_id: str
    is_theory_card: bool


def build_doc_name(namespace: str, doc_id: str, *, is_theory_card: bool = False) -> str:
    """按约定生成平台文档名（导入侧使用）。"""
    if namespace not in _NAMESPACES:
        raise ValueError(f"未知 namespace：{namespace}")
    if not doc_id.strip():
        raise ValueError("doc_id 不能为空")
    marker = f"{CARD_MARKER}_" if is_theory_card else ""
    return f"{namespace}_{marker}{doc_id}.txt"


def parse_doc_name(file_name: str) -> ParsedDocName | None:
    """把平台回传的文档名反解成 `(namespace, id)`；不符合约定时返回 `None`。

    `None` 是**有意义**的返回：调用方据此回落到内容哈希，而不是硬塞一个错的 id。
    """
    stem = str(file_name or "").strip()
    if not stem:
        return None
    if "." in stem.rsplit("/", 1)[-1]:
        stem = stem.rsplit(".", 1)[0]
    namespace, separator, remainder = stem.partition("_")
    if not separator or namespace not in _NAMESPACES or not remainder:
        return None
    is_card = remainder.startswith(f"{CARD_MARKER}_")
    doc_id = remainder[len(CARD_MARKER) + 1 :] if is_card else remainder
    if not doc_id:
        return None
    return ParsedDocName(namespace=namespace, doc_id=doc_id, is_theory_card=is_card)


__all__ = ["CARD_MARKER", "ParsedDocName", "build_doc_name", "parse_doc_name"]
