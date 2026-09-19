"""把 OpenAI 风格的 rerank 请求翻译成上游原生 rerank（D7 ③ 的转换层）。

为什么需要这个模块
------------------
平台的模型供应商（`OpenAI-API-compatible` / `YuanJing`）调用 rerank 时**只会**
`POST <endpointUrl>/rerank`，而平台配置的两家上游（DashScope 兼容模式、Ark）
**都没有这个路径**（逐个模型名实测 404）。也就是说：不提供转换层，平台的 RAG
问答就用不了（它强制要求 `rerank_model_id` 非空）。本模块就是那层翻译。

放在 `zhiyin_infrastructure/pami/` 的原因：它是**外部协议之间的适配**，不承载职引
业务规则；HTTP 进程入口在 `zhiyin_boot`（运行驱动），与 Worker 的拆分方式一致。

设计要点
--------
1. **请求侧宽容解析**：平台把 rag-wanwu 的请求体**原样**转发过来，而该形状没有公开
   schema（平台文档里就是 `additionalProperties: true`）。所以这里同时接受
   `query` / `input.query` / `question` 与 `documents` / `texts` / `passages` /
   `docs`，文档元素可以是字符串或 `{"text": ...}`。**少猜一轮**：进程入口会把收到的
   字段名打出来，第一轮就能看清真实形状。
2. **响应侧按 OpenAI 风格**：`{"results": [{"index", "relevance_score", "document"}]}`，
   因为调用方是按"OpenAI 兼容"这一约定来的。
3. **密钥不进平台库**：平台侧注册这个 rerank 模型时只填占位 Key，真实上游 Key
   由本服务从 gitignored 的 `deploy/.env` 读环境变量获得。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from zhiyin_data_sdk.errors import UnavailableError, ValidationError

#: DashScope 原生 rerank 路径（不是 OpenAI 风格，必须由本层翻译）
DASHSCOPE_RERANK_PATH = "/api/v1/services/rerank/text-rerank/text-rerank"

_QUERY_KEYS = ("query", "question", "q", "text")
_DOCUMENT_KEYS = ("documents", "docs", "texts", "passages", "candidates")


def _first_str(source: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _document_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        for key in ("text", "content", "document", "passage", "snippet"):
            value = item.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping) and isinstance(value.get("text"), str):
                return str(value["text"])
    return ""


@dataclass(frozen=True)
class RerankTranslation:
    """一次 rerank 的规范化输入。"""

    query: str
    documents: list[str]
    model: str
    top_n: int | None = None


def parse_rerank_request(
    body: Mapping[str, Any], *, default_model: str
) -> RerankTranslation:
    """把上游传来的 rerank 请求体规范成 `RerankTranslation`。

    刻意**不抛"未知字段"**：形状没有被冻结，宽容解析比严格校验更合用；但缺
    query 或 documents 时必须显式失败（静默返回空排序会让调用方以为"没有相关文档"）。
    """
    inner = body.get("input")
    scope: Mapping[str, Any] = inner if isinstance(inner, Mapping) else body

    query = _first_str(scope, _QUERY_KEYS) or _first_str(body, _QUERY_KEYS)
    raw_documents: Any = None
    for key in _DOCUMENT_KEYS:
        if isinstance(scope.get(key), list):
            raw_documents = scope[key]
            break
        if isinstance(body.get(key), list):
            raw_documents = body[key]
            break
    if not query:
        raise ValidationError(
            "rerank 请求缺少 query",
            detail={"keys": sorted(body.keys())},
        )
    if not raw_documents:
        raise ValidationError(
            "rerank 请求缺少 documents",
            detail={"keys": sorted(body.keys())},
        )
    documents = [_document_text(item) for item in raw_documents]
    model = str(scope.get("model") or body.get("model") or default_model)

    top_n: int | None = None
    for key in ("top_n", "topN", "top_k", "topK"):
        value = scope.get(key, body.get(key))
        if isinstance(value, int) and value > 0:
            top_n = value
            break
    return RerankTranslation(
        query=query, documents=documents, model=model, top_n=top_n
    )


def to_dashscope_payload(translation: RerankTranslation) -> dict[str, Any]:
    """构造 DashScope 原生 rerank 请求体。"""
    parameters: dict[str, Any] = {"return_documents": True}
    if translation.top_n:
        parameters["top_n"] = translation.top_n
    return {
        "model": translation.model,
        "input": {"query": translation.query, "documents": translation.documents},
        "parameters": parameters,
    }


def from_dashscope_response(
    payload: Mapping[str, Any], translation: RerankTranslation
) -> dict[str, Any]:
    """把 DashScope 的响应翻译成 OpenAI 风格 `results`。

    DashScope：`{"output": {"results": [{"index", "relevance_score", "document"}]}}`
    OpenAI   ：`{"results": [{"index", "relevance_score", "document"}]}`
    """
    output = payload.get("output")
    results = output.get("results") if isinstance(output, Mapping) else None
    if not isinstance(results, list):
        raise UnavailableError(
            "上游 rerank 响应缺少 results",
            detail={"keys": sorted(payload.keys())},
        )
    normalized: list[dict[str, Any]] = []
    for rank, item in enumerate(results):
        if not isinstance(item, Mapping):
            continue
        index = item.get("index")
        if not isinstance(index, int) or not 0 <= index < len(translation.documents):
            # 上游给了越界索引时回落到"第几条结果"，避免整次排序作废
            index = rank
        document = item.get("document")
        text = (
            document.get("text")
            if isinstance(document, Mapping)
            else document if isinstance(document, str) else translation.documents[index]
        )
        normalized.append(
            {
                "index": index,
                "relevance_score": float(item.get("relevance_score") or 0.0),
                "document": {"text": text},
            }
        )
    return {"results": normalized}


async def rerank(
    body: Mapping[str, Any],
    *,
    base_url: str,
    api_key: str,
    default_model: str,
    timeout_s: float = 30.0,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """完整走一次翻译：解析 → 调上游原生 rerank → 翻译回 OpenAI 风格。"""
    translation = parse_rerank_request(body, default_model=default_model)
    url = base_url.rstrip("/") + DASHSCOPE_RERANK_PATH
    payload = to_dashscope_payload(translation)
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout_s)
    try:
        response = await http.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
    except httpx.HTTPError as exc:  # 网络层失败 → 明确的"不可用"
        raise UnavailableError("调用上游 rerank 失败", cause=exc) from exc
    finally:
        if owns_client:
            await http.aclose()
    if response.status_code >= 300:
        raise UnavailableError(
            f"上游 rerank 返回 HTTP {response.status_code}",
            detail={"body": response.text[:300]},
        )
    try:
        upstream = response.json()
    except ValueError as exc:
        raise UnavailableError("上游 rerank 响应不是 JSON", cause=exc) from exc
    return from_dashscope_response(upstream, translation)


__all__ = [
    "DASHSCOPE_RERANK_PATH",
    "RerankTranslation",
    "from_dashscope_response",
    "parse_rerank_request",
    "rerank",
    "to_dashscope_payload",
]
