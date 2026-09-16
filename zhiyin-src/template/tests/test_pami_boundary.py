from __future__ import annotations

import ast
from pathlib import Path

import pytest

from zhiyin_boot.container.gateways import build_gateways
from zhiyin_boot.settings import Settings
from zhiyin_infrastructure.local.auth import DefaultPassAuth
from zhiyin_infrastructure.local.knowledge import LocalKnowledgeRepo
from zhiyin_infrastructure.local.llm import LocalOrMockLLM
from zhiyin_infrastructure.pami.adapters import PamiAuthGateway, PamiSearchGateway


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
        "ZHIYIN_USE_PAMI_KNOWLEDGE",
        "ZHIYIN_USE_PAMI_AUTH",
    ):
        monkeypatch.delenv(name, raising=False)

    gateways = build_gateways(Settings.from_env())

    assert isinstance(gateways["llm"], LocalOrMockLLM)
    assert isinstance(gateways["knowledge"], LocalKnowledgeRepo)
    assert isinstance(gateways["auth"], DefaultPassAuth)


@pytest.mark.asyncio
async def test_unimplemented_pami_search_fails_explicitly() -> None:
    gateway = PamiSearchGateway()
    with pytest.raises(NotImplementedError, match="尚未实现"):
        await gateway.keyword("career")


@pytest.mark.asyncio
async def test_unimplemented_pami_auth_fails_explicitly() -> None:
    gateway = PamiAuthGateway("http://nginx:8081")
    with pytest.raises(NotImplementedError, match="尚未实现"):
        await gateway.authenticate({})


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
