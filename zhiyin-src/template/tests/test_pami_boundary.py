from __future__ import annotations

import ast
import json
from pathlib import Path

import httpx
import pytest

from zhiyin_boot.container.gateways import build_gateways
from zhiyin_boot.settings import Settings
from zhiyin_infrastructure.local.auth import DefaultPassAuth
from zhiyin_infrastructure.local.knowledge import LocalSearchGateway
from zhiyin_infrastructure.local.llm import LocalOrMockLLM
from zhiyin_infrastructure.pami.adapters import (
    PamiAuthGateway,
    PamiEmbedGateway,
    PamiLLMGateway,
    PamiSearchGateway,
)
from zhiyin_data_sdk.errors import UnavailableError
from zhiyin_data_sdk.gateways.ai import LLMMessage
from zhiyin_kernel.enums import UserRole
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalQuery


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TEMPLATE_ROOT.parents[1]
PACKAGE_ROOTS = (
    "zhiyin-api",
    "zhiyin-business",
    "zhiyin-orchestration",
    "zhiyin-data-sdk",
    "zhiyin-infrastructure",
    "zhiyin-boot",
)


def test_default_gateway_wiring_remains_local(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ZHIYIN_USE_PAMI_LLM",
        "ZHIYIN_USE_PAMI_EMBEDDING",
        "ZHIYIN_USE_PAMI_SEARCH",
        "ZHIYIN_USE_PAMI_AUTH",
    ):
        monkeypatch.delenv(name, raising=False)

    gateways = build_gateways(Settings.from_env())

    assert isinstance(gateways["llm"], LocalOrMockLLM)
    assert isinstance(gateways["search"], LocalSearchGateway)
    assert isinstance(gateways["auth"], DefaultPassAuth)


@pytest.mark.asyncio
async def test_pami_agent_adapter_maps_conversation_and_structured_result() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/conversation"):
            return httpx.Response(200, json={"data": {"conversationId": "conv-1"}})
        return httpx.Response(
            200,
            json={"response": '{"answer":"ok"}', "usage": {"total_tokens": 9}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = PamiLLMGateway("http://nginx:8081", "api-key", client=client)
        result = await gateway.chat(
            [LLMMessage(role="user", content="测试")],
            json_schema={"type": "object"},
        )

    assert result.structured == {"answer": "ok"}
    assert len(requests) == 2
    assert requests[0].headers["authorization"] == "Bearer api-key"
    assert json.loads(requests[1].content)["conversation_id"] == "conv-1"


@pytest.mark.asyncio
async def test_pami_rag_maps_unified_search_hits() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "output": "answer",
                    "searchList": [
                        {"title": "RIASEC", "snippet": "兴趣理论", "score": 0.8}
                    ],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        search = PamiSearchGateway("http://nginx:8081", "api-key", client=client)
        hits = await search.search(
            RetrievalQuery(
                query="职业兴趣", namespace=RetrievalNamespace.THEORY,
                mode="keyword"
            )
        )

    assert hits[0].metadata["provider"] == "pami-rag"
    assert hits[0].metadata["namespace"] == "theory"
    assert hits[0].content == "兴趣理论"
    # D11：三条通道（本地关键词 / PAMI / 向量）统一按 `namespace:id` 出 id
    assert hits[0].evidence_id.startswith("theory:"), hits[0].evidence_id


@pytest.mark.asyncio
async def test_pami_search_rejects_raw_vector_explicitly() -> None:
    search = PamiSearchGateway("http://nginx:8081", "api-key")
    with pytest.raises(UnavailableError, match="裸向量"):
        await search.search(
            RetrievalQuery(
                query="职业兴趣", namespace=RetrievalNamespace.THEORY,
                mode="vector"
            )
        )


@pytest.mark.asyncio
async def test_pami_auth_uses_remote_user_info() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "userId": "u-1",
                    "nickname": "数据负责人",
                    "orgs": [{"roles": [{"name": "admin"}]}],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = PamiAuthGateway(
            "http://nginx:8081", org_id="org-1", client=client
        )
        principal = await gateway.authenticate(
            {"headers": {"Authorization": "Bearer user-token"}}
        )

    assert principal.user_id == "u-1"
    assert principal.role == UserRole.ADMIN
    assert seen[0].headers["x-org-id"] == "org-1"
    assert seen[0].headers["authorization"] == "Bearer user-token"


@pytest.mark.asyncio
async def test_pami_embedding_enforces_1024_dimensions() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"embeddings": [[0.1] * 1024]}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = PamiEmbedGateway(
            "http://nginx:8081", "embedding-model", client=client
        )
        vectors = await gateway.embed(["职业"])

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024


def test_wanwu_is_not_a_zhiyin_python_package() -> None:
    pyproject = (TEMPLATE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "platform/wanwu" not in pyproject
    assert "platform.wanwu" not in pyproject


def test_zhiyin_packages_do_not_import_wanwu_source() -> None:
    violations: list[str] = []
    for root_name in PACKAGE_ROOTS:
        for source in (TEMPLATE_ROOT / root_name).rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    names = []
                if {"wanwu", "platform"} & set(names):
                    violations.append(str(source.relative_to(REPO_ROOT)))
    assert violations == []
