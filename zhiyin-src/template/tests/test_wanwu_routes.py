from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "scripts" / "verify_wanwu_routes.py"
MANIFEST = REPO_ROOT / "deploy" / "wanwu-routes.json"
NGINX = (
    REPO_ROOT
    / "platform"
    / "wanwu"
    / "configs"
    / "middleware"
    / "nginx"
    / "conf.d"
    / "aibase.conf"
)


def _load_verifier():
    if not VERIFIER.is_file():
        pytest.fail("Wanwu route verifier is missing")
    spec = importlib.util.spec_from_file_location("verify_wanwu_routes", VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validator_reports_missing_route_and_wrong_upstream(tmp_path: Path) -> None:
    manifest = tmp_path / "routes.json"
    nginx = tmp_path / "nginx.conf"
    manifest.write_text(
        json.dumps(
            {
                "routes": [
                    {"prefix": "/user/api/", "upstream": "http://bff-service:6668/"},
                    {"prefix": "/service/api/", "upstream": "http://bff-service:6668/"},
                ]
            }
        ),
        encoding="utf-8",
    )
    nginx.write_text(
        "location ^~ /user/api/ {\n    proxy_pass http://wrong:9999/;\n}\n",
        encoding="utf-8",
    )

    errors = _load_verifier().validate_routes(manifest, nginx)

    assert errors == [
        "upstream mismatch for /user/api/: "
        "expected http://bff-service:6668/, got http://wrong:9999/",
        "missing nginx location: /service/api/",
    ]


def test_checked_in_wanwu_routes_match_nginx() -> None:
    assert _load_verifier().validate_routes(MANIFEST, NGINX) == []
