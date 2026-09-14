"""接口层测试：应用能起来、统一信封生效、未实现能力按约定降级。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zhiyin_api.app import API_PREFIX
from zhiyin_boot import Settings, build_container, wire_application
from zhiyin_api.app import create_app
from zhiyin_api.dto.common import ErrorCode


@pytest.fixture
def settings() -> Settings:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    return Settings(
        env="test",
        local_registry_dir=str(data_dir / "registry"),
        local_knowledge_dir=str(data_dir / "knowledge"),
        local_object_dir=str(data_dir / "objects"),
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = wire_application(build_container(settings))
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_reports_assembly(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assembly = body["assembly"]
    # 已实现的部件必须如实报 wired
    assert assembly["orchestration"]["agent_engine"] == "wired"
    assert assembly["services"]["loop"] == "wired"
    # 未实现的部件必须如实报 not_wired，而不是装作装好了
    assert assembly["services"]["facade"] == "not_wired"
    assert assembly["missing"]


def test_openapi_is_served(client: TestClient) -> None:
    """有 app 工厂的直接收益：/docs 与 openapi.json 可用，前端能生成类型。"""
    response = client.get(f"{API_PREFIX}/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    # 业务接口一律在版本前缀下（见 tests/test_api_prefix.py 的守卫）
    assert f"{API_PREFIX}/app/bootstrap" in paths
    assert f"{API_PREFIX}/app/task/enter" in paths
    assert "/healthz" in paths


def test_unimplemented_capability_degrades_instead_of_500(client: TestClient) -> None:
    """第一期 Facade 未实现：接口按 DEPENDENCY_UNAVAILABLE 降级，不返回 500（§6.2）。"""
    response = client.get(f"{API_PREFIX}/app/bootstrap")
    assert response.status_code == 503

    body = response.json()
    assert body["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE
    assert body["message"]
    # 统一信封字段齐备（R-API-006）
    assert set(body) >= {"code", "message", "data", "trace_id"}


def test_healthz_works_without_assembly() -> None:
    """裸 create_app（未走 boot）时 healthz 仍可用，返回空装配报告。"""
    from zhiyin_api.runtime import reset_runtime

    reset_runtime()
    with TestClient(create_app()) as bare:
        response = bare.get("/healthz")
        assert response.status_code == 200
        assert response.json()["assembly"]["gateways"] == {}
