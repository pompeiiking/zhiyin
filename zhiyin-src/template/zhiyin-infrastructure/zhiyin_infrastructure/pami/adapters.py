"""pami 适配器实现（骨架）。

替换方式：在 zhiyin-boot 的 container 里把 local/* 换成 pami/*，上层零改动。
降级要求（R-SDK-009）：pami 不可用时必须返回 degraded=True 的降级结果或抛
UnavailableError，由调用方决定是否回落本地实现，禁止直接 500。
"""

from __future__ import annotations

from typing import Any, Optional

from zhiyin_data_sdk.gateways.ai import (
    KnowledgeGateway,
    KnowledgeHit,
    LLMGateway,
    LLMMessage,
    LLMResult,
    SearchGateway,
    SearchHit,
)
from zhiyin_data_sdk.gateways.security import AuthGateway, AuthPrincipal


class PamiLLMGateway(LLMGateway):
    """pami 模型服务适配器。"""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 60.0) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._timeout_s = timeout_s

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
        timeout_s: float = 60.0,
    ) -> LLMResult:
        """TODO(骨架): 走 pami OpenAPI，json_schema 非空时要求结构化输出。"""
        raise NotImplementedError("TODO(骨架): PamiLLMGateway.chat 尚未实现")


class PamiKnowledgeGateway(KnowledgeGateway):
    """pami 知识库检索适配器。"""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        namespace: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[KnowledgeHit]:
        """TODO(骨架): 走 pami 知识库检索（含 RAG）。"""
        raise NotImplementedError("TODO(骨架): PamiKnowledgeGateway.search 尚未实现")


class PamiSearchGateway(SearchGateway):
    """pami 检索适配器。"""

    async def keyword(self, query: str, *, top_k: int = 10) -> list[SearchHit]:
        raise NotImplementedError("TODO(骨架): PamiSearchGateway.keyword 尚未实现")

    async def vector(self, embedding: list[float], *, top_k: int = 10) -> list[SearchHit]:
        raise NotImplementedError("TODO(骨架): PamiSearchGateway.vector 尚未实现")

    async def hybrid(self, query: str, *, top_k: int = 10) -> list[SearchHit]:
        raise NotImplementedError("TODO(骨架): PamiSearchGateway.hybrid 尚未实现")


class PamiAuthGateway(AuthGateway):
    """pami IAM 鉴权适配器（JWT 服务账号 / APIKey）。"""

    def __init__(self, base_url: str, jwt_secret: str = "") -> None:
        self._base_url = base_url
        self._jwt_secret = jwt_secret

    async def authenticate(self, request: dict[str, Any]) -> AuthPrincipal:
        """TODO(骨架): 解析并校验 pami 签发的 JWT，映射为 AuthPrincipal。"""
        raise NotImplementedError("TODO(骨架): PamiAuthGateway.authenticate 尚未实现")

    async def is_authenticated(self, request: dict[str, Any]) -> bool:
        raise NotImplementedError("TODO(骨架): PamiAuthGateway.is_authenticated 尚未实现")
