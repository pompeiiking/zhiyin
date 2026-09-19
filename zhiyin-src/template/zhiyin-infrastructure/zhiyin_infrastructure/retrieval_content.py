"""第三期 RAG 内容校验、规范化与稳定切片。"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

from zhiyin_kernel.enums import RetrievalNamespace


def validate_retrieval_document(
    document: dict[str, Any], schema: dict[str, Any]
) -> None:
    """按仓库中的命名空间 Schema 校验入库前文档。"""
    try:
        namespace = RetrievalNamespace(str(document["namespace"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("检索文档 namespace 未登记") from exc
    specification = schema.get("namespaces", {}).get(namespace.value)
    if not isinstance(specification, dict):
        raise ValueError(f"检索 Schema 缺少命名空间：{namespace.value}")
    required = set(schema.get("common_required", [])) | set(
        specification.get("required", [])
    )
    missing = sorted(
        field for field in required if document.get(field) is None or document.get(field) == ""
    )
    if missing:
        raise ValueError(f"检索文档缺少必填字段：{', '.join(missing)}")
    if document.get("status") not in set(schema.get("production_index_status", [])):
        raise ValueError("只有 enabled 文档可以进入生产索引")
    if specification.get("visibility") == "private":
        if not document.get("org_id") or not document.get("user_id"):
            raise ValueError("私有检索文档必须绑定 org_id 与 user_id")


def load_retrieval_schema(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("检索 Schema 根节点必须是对象")
    return raw


def chunk_retrieval_document(
    document: dict[str, Any], *, max_chars: int = 800, overlap_chars: int = 120
) -> list[dict[str, Any]]:
    """按段落/句子切片并生成跨重跑稳定的 chunk_id。"""
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("切片长度必须为正，且 overlap_chars 小于 max_chars")
    namespace = RetrievalNamespace(str(document["namespace"]))
    source_id = str(document.get("source_id") or "").strip()
    document_id = str(document.get("id") or "").strip()
    content = str(document.get("content") or document.get("summary") or "").strip()
    if not source_id or not document_id or not content:
        raise ValueError("切片要求 id、source_id 与 content/summary")
    parts = [part.strip() for part in re.split(r"(?<=[。！？；\n])", content) if part.strip()]
    windows: list[str] = []
    current = ""
    for part in parts:
        while len(part) > max_chars:
            if current:
                windows.append(current)
                current = ""
            windows.append(part[:max_chars])
            part = part[max_chars - overlap_chars :]
        if current and len(current) + len(part) > max_chars:
            windows.append(current)
            current = current[-overlap_chars:] + part
        else:
            current += part
    if current:
        windows.append(current)
    chunks: list[dict[str, Any]] = []
    for index, text in enumerate(windows):
        fingerprint = sha256(
            f"{namespace.value}\0{source_id}\0{document_id}\0{index}\0{text}".encode("utf-8")
        ).hexdigest()
        chunks.append(
            {
                "id": f"{document_id}:chunk:{fingerprint[:16]}",
                "document_id": document_id,
                "source_id": source_id,
                "namespace": namespace.value,
                "chunk_index": index,
                "content": text,
                "content_hash": sha256(text.encode("utf-8")).hexdigest(),
                "version": int(document.get("version") or 1),
                "metadata": {
                    key: value
                    for key, value in document.items()
                    if key not in {"content", "summary"}
                },
            }
        )
    return chunks


def validate_documents(
    documents: Iterable[dict[str, Any]], schema: dict[str, Any]
) -> list[dict[str, Any]]:
    validated = []
    for document in documents:
        validate_retrieval_document(document, schema)
        validated.append(document)
    return validated


__all__ = [
    "chunk_retrieval_document",
    "load_retrieval_schema",
    "validate_documents",
    "validate_retrieval_document",
]
