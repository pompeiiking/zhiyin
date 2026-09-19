"""PAMI（内置 Wanwu）HTTP 适配器。

本模块只做 Data SDK 契约与 PAMI 原生 HTTP 契约之间的转换。PAMI 返回的
``code/msg/data``、Agent 顶层响应和 RAG ``data.output`` 形状不同，必须分别解析；
网络错误、非 2xx 与平台业务错误统一映射为 :class:`UnavailableError`。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import httpx

from zhiyin_data_sdk.errors import UnavailableError, ValidationError
from zhiyin_data_sdk.gateways.ai import (
    EmbedGateway,
    LLMGateway,
    LLMMessage,
    LLMResult,
    SearchGateway,
)
from zhiyin_data_sdk.gateways.security import AuthGateway, AuthPrincipal
from zhiyin_kernel.enums import RetrievalNamespace, UserRole
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery

from .doc_naming import parse_doc_name

#: **私有域**：内容只属于某个用户/组织，平台 OpenAPI 表达不了这种隔离，因此不得走 PAMI。
#: 依据《第三期 RAG 检索内容与检索流程设计》§4.2 的域归属表与 §6.3 的隔离要求。
PRIVATE_NAMESPACES = frozenset(
    {
        RetrievalNamespace.REPORT,
        RetrievalNamespace.RESUME,
        RetrievalNamespace.MEMORY,
    }
)


def _clean_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        raise ValueError("PAMI base_url 必须是 http(s) 地址")
    return value


class _PamiHttp:
    def __init__(
        self,
        base_url: str,
        *,
        credential: str = "",
        org_id: str = "",
        timeout_s: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = _clean_base_url(base_url)
        self.credential = credential.strip()
        self.org_id = org_id.strip()
        self.timeout_s = timeout_s
        self.client = client

    async def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        credential: str | None = None,
        org_id: str | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        token = self.credential if credential is None else credential.strip()
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        actual_org = self.org_id if org_id is None else org_id.strip()
        if actual_org:
            headers["X-Org-Id"] = actual_org
        request_timeout = timeout_s or self.timeout_s
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=request_timeout)
        try:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                json=payload,
                timeout=request_timeout,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UnavailableError(
                "PAMI 接口不可用",
                detail={"method": method, "path": path},
                cause=exc,
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        if not isinstance(body, dict):
            raise UnavailableError(
                "PAMI 返回了非对象 JSON", detail={"method": method, "path": path}
            )
        code = body.get("code")
        if code not in (None, 0, 200, "0", "200"):
            raise UnavailableError(
                "PAMI 返回业务错误",
                detail={
                    "method": method,
                    "path": path,
                    "code": code,
                    "message": str(body.get("msg") or body.get("message") or ""),
                },
            )
        return body


def _message_query(messages: list[LLMMessage], json_schema: dict[str, Any] | None) -> str:
    lines = [f"[{message.role}] {message.content}" for message in messages]
    if json_schema is not None:
        schema = json.dumps(json_schema, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"请只返回符合以下 JSON Schema 的 JSON 对象，不要添加 Markdown：{schema}")
    return "\n".join(lines)


def _extract_conversation_id(body: dict[str, Any]) -> str:
    candidates: list[Any] = [
        body.get("conversation_id"),
        body.get("conversationId"),
        body.get("id"),
    ]
    data = body.get("data")
    if isinstance(data, dict):
        candidates.extend(
            [data.get("conversation_id"), data.get("conversationId"), data.get("id")]
        )
    elif isinstance(data, str):
        candidates.append(data)
    for value in candidates:
        if value:
            return str(value)
    raise UnavailableError("PAMI 创建会话响应缺少 conversation_id")


def _parse_structured(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


class PamiLLMGateway(LLMGateway):
    """通过已发布 PAMI Agent 的 OpenAPI 完成非流式模型调用。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_s: float = 60.0,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("启用 PAMI LLM 时必须配置应用 API Key")
        self._http = _PamiHttp(
            base_url, credential=api_key, timeout_s=timeout_s, client=client
        )

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
        timeout_s: float = 60.0,
    ) -> LLMResult:
        del temperature  # PAMI Agent OpenAPI 当前契约不暴露 temperature。
        conversation = await self._http.request(
            "POST",
            "/service/api/openapi/v1/agent/conversation",
            payload={"title": "zhiyin-gateway"},
            timeout_s=timeout_s,
        )
        conversation_id = _extract_conversation_id(conversation)
        body = await self._http.request(
            "POST",
            "/service/api/openapi/v1/agent/chat",
            payload={
                "conversation_id": conversation_id,
                "query": _message_query(messages, json_schema),
                "stream": False,
            },
            timeout_s=timeout_s,
        )
        text = str(body.get("response") or body.get("message") or "")
        structured = _parse_structured(text) if json_schema is not None else None
        if json_schema is not None and structured is None:
            raise ValidationError("PAMI Agent 未返回合法的结构化 JSON")
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        return LLMResult(
            text=text,
            structured=structured,
            model="pami-agent",
            usage=dict(usage),
            degraded=False,
        )


class PamiEmbedGateway(EmbedGateway):
    """调用 PAMI 模型回调代理生成统一 1024 维嵌入。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        base_url: str,
        model_id: str,
        *,
        dimension: int = 1024,
        timeout_s: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not model_id.strip():
            raise ValueError("启用 PAMI Embedding 时必须配置 model_id")
        if dimension != 1024:
            raise ValueError("M3 决策要求 Embedding 统一使用 1024 维")
        self._model_id = model_id.strip()
        self._dimension = dimension
        self._http = _PamiHttp(base_url, timeout_s=timeout_s, client=client)

    @property
    def model_id(self) -> str:
        return self._model_id

    async def embed(
        self, texts: list[str], *, timeout_s: float = 30.0
    ) -> list[list[float]]:
        if not texts:
            return []
        body = await self._http.request(
            "POST",
            f"/service/api/callback/v1/model/{self._model_id}/embeddings",
            payload={
                "input": texts,
                "model": self._model_id,
                "dimensions": self._dimension,
            },
            timeout_s=timeout_s,
        )
        payload: Any = body.get("data", body)
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            payload = payload["data"]
        if isinstance(payload, dict) and isinstance(payload.get("embeddings"), list):
            vectors = payload["embeddings"]
        elif isinstance(payload, list):
            vectors = [
                item.get("embedding") if isinstance(item, dict) else item for item in payload
            ]
        else:
            raise UnavailableError("PAMI Embedding 响应缺少向量列表")
        if len(vectors) != len(texts):
            raise UnavailableError("PAMI Embedding 返回数量与输入不一致")
        normalized: list[list[float]] = []
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != self._dimension:
                raise UnavailableError("PAMI Embedding 返回维度不是 1024")
            normalized.append([float(value) for value in vector])
        return normalized


def _search_hits(body: dict[str, Any], request: RetrievalQuery) -> list[RetrievalEvidence]:
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    raw_hits = data.get("searchList") or body.get("search_list") or []
    if not isinstance(raw_hits, list):
        return []
    hits: list[RetrievalEvidence] = []
    for index, item in enumerate(raw_hits):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        snippet = str(item.get("snippet") or "")
        knowledge_base = str(item.get("kb_name") or "")
        stable = hashlib.sha256(
            f"{knowledge_base}\0{title}\0{snippet}".encode("utf-8")
        ).hexdigest()[:24]
        # 平台不回文档 id（响应只有 kb_name/title/snippet）。但**文件名是我们自己定的**，
        # 按约定可反解出 `(namespace, id)`——这是唯一能让权威回填与引用溯源对上的线索。
        # 反解失败时回落到内容哈希：宁可"溯源缺一条"，也不要猜一个错的 id 让权威表静默失配。
        parsed = parse_doc_name(title)
        source_id = str(item.get("source_id") or item.get("doc_id") or "")
        if parsed is not None and parsed.namespace == request.namespace.value:
            source_id = source_id or parsed.doc_id
            evidence_id = f"{request.namespace.value}:{parsed.doc_id}"
        else:
            evidence_id = f"{request.namespace.value}:{stable or index}"
        hits.append(
            RetrievalEvidence(
                evidence_id=evidence_id,
                namespace=request.namespace,
                source_id=source_id,
                source_url=str(item.get("source_url") or item.get("url") or ""),
                title=title,
                content=snippet or title,
                score=float(item.get("score") or 0.0),
                # 是不是演示内容由**权威表那一行**决定（平台不回这个信息）：
                # `hydrate` 会以 `{**row.metadata_json, **hit.metadata}` 合并，
                # 所以权威行里的 `demo=True` 不会被这里覆盖掉，D12 的护栏照常生效。
                metadata={
                    "provider": "pami-rag",
                    "knowledge_base": knowledge_base,
                    "namespace": request.namespace.value,
                    "doc_name": title,
                    "doc_kind": "theory_card"
                    if (parsed is not None and parsed.is_theory_card)
                    else "doc",
                    "id_parsed": parsed is not None,
                },
            )
        )
    return hits


class PamiSearchGateway(SearchGateway):
    """通过已发布 PAMI RAG 应用提供统一检索。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_s: float = 60.0,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("启用 PAMI Search 时必须配置 RAG 应用 API Key")
        self._http = _PamiHttp(
            base_url, credential=api_key, timeout_s=timeout_s, client=client
        )

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        if request.mode == "vector":
            raise UnavailableError("PAMI RAG OpenAPI 不接受调用方提供的裸向量")
        # ⚠️ **私有域不得走 PAMI**：《第三期设计》§6.3 明确"公共知识与用户私有知识不能
        # 绑定到同一个无隔离应用；如果 PAMI 不能表达用户级权限、版本和时效过滤，则私有域
        # 不能直接走此路径"。平台 OpenAPI 的请求体只有 `query/stream`，确实无法表达
        # 用户级隔离——所以这里**必须拒绝**，让 RRF 降级到向量通道（那条会按 org/user 过滤）。
        #
        # 这一条是我上一轮引入的问题的补丁：把"带 filters 就抛错"放宽成"忽略 filters"之后，
        # 私有域查询会**拿到公共知识当结果**（过滤被忽略），既不符合口径也会污染私有域证据。
        if request.namespace in PRIVATE_NAMESPACES or "user_id" in (request.filters or {}):
            raise UnavailableError(
                "私有域检索不能走 PAMI RAG（平台无法表达用户级隔离）",
                detail={"namespace": request.namespace.value},
            )
        # 公共域：PAMI 的请求体只有 query/stream，**不接受** metadata filters。这里不是把
        # filters 当作"已生效"：命中会带 `metadata["filters_ignored"]`，让调用方看得见
        # "这次过滤没被服务端执行"。原先"带 filters 就抛错"会把关键词通道整条打挂
        # （编排器每条 query 都带 `status=enabled`），启用 PAMI 后真实对话检索恒为 0。
        # `status=enabled` 在 PAMI 侧本就成立（只有启用文档会被索引），因此忽略比整条失败
        # 更合理；关键是**忽略也要可见**（与 D12/D13 同一条原则）。
        ignored_filters = dict(request.filters or {})
        body = await self._http.request(
            "POST",
            "/service/api/openapi/v1/rag/chat",
            # 实际知识范围由 API Key 所绑定的 RAG 应用决定；不能把 namespace
            # 拼入自然语言后冒充服务端隔离。namespace 只作为命中来源标签返回。
            payload={"query": request.query, "stream": False},
        )
        hits = _search_hits(body, request)[: request.top_k]
        if ignored_filters:
            hits = [
                hit.model_copy(
                    update={
                        "metadata": {
                            **hit.metadata,
                            "filters_ignored": ignored_filters,
                        }
                    }
                )
                for hit in hits
            ]
        return hits


def _request_headers(request: dict[str, Any]) -> dict[str, str]:
    raw = request.get("headers", request)
    if not isinstance(raw, dict):
        return {}
    return {str(key).lower(): str(value) for key, value in raw.items()}


class PamiAuthGateway(AuthGateway):
    """通过 PAMI ``user/info`` 验证 JWT 并映射职引主体。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        base_url: str,
        jwt_secret: str = "",
        *,
        org_id: str = "",
        timeout_s: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        del jwt_secret  # 不在职引侧复制 PAMI 的签名密钥，统一远程验签。
        self._http = _PamiHttp(
            base_url, org_id=org_id, timeout_s=timeout_s, client=client
        )

    async def authenticate(self, request: dict[str, Any]) -> AuthPrincipal:
        headers = _request_headers(request)
        authorization = headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            raise UnavailableError("请求缺少 PAMI Bearer Token")
        token = authorization.split(" ", 1)[1].strip()
        org_id = headers.get("x-org-id", self._http.org_id)
        body = await self._http.request(
            "GET",
            "/user/api/v1/user/info",
            credential=token,
            org_id=org_id,
        )
        data = body.get("data")
        if not isinstance(data, dict) or not (data.get("userId") or data.get("uid")):
            raise UnavailableError("PAMI user/info 响应缺少用户标识")
        role_names = {
            str(role.get("name", "")).lower()
            for org in data.get("orgs", [])
            if isinstance(org, dict)
            for role in org.get("roles", [])
            if isinstance(role, dict)
        }
        if any("admin" in role or "管理员" in role for role in role_names):
            role = UserRole.ADMIN
        elif any("mentor" in role or "导师" in role for role in role_names):
            role = UserRole.MENTOR
        else:
            role = UserRole.STUDENT
        return AuthPrincipal(
            user_id=str(data.get("userId") or data.get("uid")),
            role=role,
            display_name=str(data.get("nickname") or data.get("username") or ""),
            is_guest=False,
            raw_claims={
                "provider": "pami",
                "org_id": org_id,
                "username": str(data.get("username") or ""),
            },
        )

    async def is_authenticated(self, request: dict[str, Any]) -> bool:
        try:
            await self.authenticate(request)
        except UnavailableError:
            return False
        return True


__all__ = [
    "PamiAuthGateway",
    "PamiEmbedGateway",
    "PamiLLMGateway",
    "PamiSearchGateway",
]
