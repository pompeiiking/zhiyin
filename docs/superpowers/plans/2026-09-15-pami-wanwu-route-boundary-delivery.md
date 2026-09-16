# pami/zhiyinbase Route and Boundary Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete stages 3–5 of the approved zhiyinbase source-and-interface exposure design without re-importing the existing zhiyinbase snapshot.

**Architecture:** zhiyinbase remains independent under `platform/wanwu` and exposes native routes through its own Nginx/BFF. Zhiyin keeps its `/api/v1/*` product API and disabled pami skeletons; executable checks enforce route configuration and package boundaries.

**Tech Stack:** Python 3.10+, pytest, JSON, Nginx configuration, Docker Compose, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-09-15-pami-wanwu-integration-design.md`

## Global Constraints

- Keep imported revision `969a74c7c376169d2a88c72891807d35bb40861b`; do not re-import it.
- Do not add a zhiyinbase proxy route to `zhiyin-api`.
- Do not implement real pami HTTP calls or enable `ZHIYIN_USE_PAMI_*`.
- Keep zhiyinbase authentication, permission, API Key, callback, and streaming behavior unchanged.
- Keep zhiyinbase internal service ports removed by the Compose override.
- Treat route presence as configuration evidence, not proof of a successful business request.
- Preserve all existing Zhiyin tests, lint, OpenAPI, frontend, and phase-one checks.

## Current Baseline

Stages 1 and 2 are already represented by:

- `scripts/import_wanwu.py`;
- `platform/wanwu/.zhiyin-vendor.json` and `UPSTREAM.md`;
- `zhiyin-src/template/Dockerfile`;
- `deploy/compose.yaml`, environment initialization, and lifecycle scripts;
- source, container, and Compose checks in CI.

## File Map

| File | Responsibility |
| --- | --- |
| `scripts/verify_wanwu_routes.py` | Parse and validate native Nginx routes against a checked-in contract |
| `deploy/wanwu-routes.json` | Route prefixes, upstream targets, trust surfaces, and documentation anchors |
| `zhiyin-src/template/tests/test_wanwu_routes.py` | Test verifier behavior using controlled configuration and the checked-in assets |
| `zhiyin-src/template/tests/test_pami_boundary.py` | Verify default local wiring, explicit pami skeleton failure, and source boundaries |
| `.github/workflows/ci.yml` | Execute route and boundary verification |
| `README.md`, `docs/README.md` | State and index the delivered scope |
| earlier source/deployment plan | Mark stages 1–2 as the retained baseline |

---

### Task 1: Build an Executable zhiyinbase Route Contract

**Files:**
- Create: `scripts/verify_wanwu_routes.py`
- Create: `deploy/wanwu-routes.json`
- Create: `zhiyin-src/template/tests/test_wanwu_routes.py`

**Interfaces:**
- Produces: `validate_routes(manifest_path: Path, nginx_path: Path) -> list[str]`
- Produces: CLI exit 0 for a matching route contract and exit 1 with diagnostics otherwise

- [ ] **Step 1: Write the failing behavior test**

Create `test_wanwu_routes.py` with a dynamic loader that calls `pytest.fail`
when the verifier does not exist. Use a temporary manifest with one missing route
and one wrong upstream, then assert these literal diagnostics:

```python
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "scripts" / "verify_wanwu_routes.py"
MANIFEST = REPO_ROOT / "deploy" / "wanwu-routes.json"
NGINX = REPO_ROOT / "platform" / "wanwu" / "configs" / "middleware" / "nginx" / "conf.d" / "aibase.conf"


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
        "upstream mismatch for /user/api/: expected http://bff-service:6668/, got http://wrong:9999/",
        "missing nginx location: /service/api/",
    ]
```

- [ ] **Step 2: Run RED**

Run `python -m pytest tests/test_wanwu_routes.py -v` from
`zhiyin-src/template`.

Expected: FAIL with `Wanwu route verifier is missing`.

- [ ] **Step 3: Implement the route verifier**

Create `scripts/verify_wanwu_routes.py` with:

- `parse_nginx_routes(text: str) -> dict[str, str]` using a location-block
  regex and a `proxy_pass` regex;
- `validate_routes(...)` that returns the exact ordered diagnostics above;
- an argparse CLI with defaults pointing to the checked-in manifest and Nginx file;
- one diagnostic per line on stderr and exit 1 when validation fails.

- [ ] **Step 4: Add the checked-in route manifest**

Create five entries:

| Prefix | Upstream | Trust surface |
| --- | --- | --- |
| `/user/api/` | `http://bff-service:6668/` | `wanwu-jwt-and-permissions` |
| `/use/model/api/` | `http://bff-service:6668/` | `wanwu-model-middleware` |
| `/service/api/` | `http://bff-service:6668/` | `per-route-jwt-api-key-or-open-rule` |
| `/workflow/api/` | `http://agentscope-wanwu:6672/` | `wanwu-workflow-protocol` |
| `/minio/download/api/` | `http://minio-wanwu:9000/` | `wanwu-minio-download-rule` |

Top-level fields are `entrypoint: wanwu-nginx`,
`local_url: http://127.0.0.1:8081`, and `claim: route-configured`.

- [ ] **Step 5: Add the checked-in-assets test**

Append:

```python
def test_checked_in_wanwu_routes_match_nginx() -> None:
    assert _load_verifier().validate_routes(MANIFEST, NGINX) == []
```

- [ ] **Step 6: Run GREEN and the CLI**

Run:

```powershell
python -m pytest tests/test_wanwu_routes.py -v
python ../../scripts/verify_wanwu_routes.py
```

Expected: 2 passed and CLI exit 0.

- [ ] **Step 7: Commit**

```powershell
git add ../../scripts/verify_wanwu_routes.py ../../deploy/wanwu-routes.json tests/test_wanwu_routes.py
git commit -m "test: verify wanwu native route exposure"
```

---

### Task 2: Verify Documentation Anchors and Host Isolation

**Files:**
- Modify: `zhiyin-src/template/tests/test_wanwu_routes.py`
- Modify: `scripts/verify_wanwu_routes.py`
- Modify: `deploy/wanwu-routes.json`

**Interfaces:**
- Extends the route contract with `documentation_anchor`
- Adds `validate_documentation(manifest_path: Path, document_paths: list[Path]) -> list[str]`

- [ ] **Step 1: Write RED tests**

Add controlled tests proving that an absent documentation anchor returns
`undocumented route: /minio/download/api/`. Add a checked-in-assets test that
loads both `接口.md` and `08-接口与通信架构.md`.

Add a repository behavior test that loads the merged Compose model as text and
asserts the override resets ports for `mysql`, `redis`, `minio`, `kafka`,
`es`, `bff-service`, `agentscope`, `rag`, and `agent`, while Nginx is
bound to `127.0.0.1:8081`.

- [ ] **Step 2: Run RED**

Run `python -m pytest tests/test_wanwu_routes.py -v`.

Expected: FAIL because `validate_documentation` is missing.

- [ ] **Step 3: Implement documentation validation**

For each manifest route, require its literal `documentation_anchor` to appear in
at least one supplied document. Add these anchors:

- `/user/api/v1/`;
- `/use/model/api/`;
- `/service/api/openapi/v1/`;
- `/workflow/api/`;
- `/minio/download/api/`.

Return errors in manifest order and do not infer methods, fields, authentication,
or success status.

- [ ] **Step 4: Run GREEN**

Run `python -m pytest tests/test_wanwu_routes.py -v`.

Expected: all route tests pass.

- [ ] **Step 5: Commit**

```powershell
git add ../../scripts/verify_wanwu_routes.py ../../deploy/wanwu-routes.json tests/test_wanwu_routes.py
git commit -m "test: anchor wanwu routes to platform documentation"
```

---

### Task 3: Lock the Zhiyin/Pami Boundary

**Files:**
- Create: `zhiyin-src/template/tests/test_pami_boundary.py`

**Interfaces:**
- Consumes: `Settings.from_env()`, `build_gateways(settings)`, and existing pami skeleton adapters
- Produces: executable evidence that normal wiring remains local and pami skeletons fail explicitly

- [ ] **Step 1: Write local-wiring characterization tests**

Clear `ZHIYIN_USE_PAMI_LLM`, `ZHIYIN_USE_PAMI_KNOWLEDGE`, and
`ZHIYIN_USE_PAMI_AUTH` with `monkeypatch.delenv`. Build settings with
`Settings.from_env()`, call `build_gateways(settings)`, and assert the concrete
classes are `LocalOrMockLLM`, `LocalKnowledgeRepo`, and `DefaultPassAuth`.

- [ ] **Step 2: Add explicit-failure tests**

Use `pytest.mark.asyncio` and assert:

- `PamiSearchGateway().keyword("career")` raises `NotImplementedError`
  containing `尚未实现`;
- `PamiAuthGateway("http://nginx:8081").authenticate({})` raises the same
  explicit marker.

- [ ] **Step 3: Add the source-boundary test**

Parse every Python file under the seven Zhiyin package roots with `ast`.
Fail when an absolute import root is `wanwu` or `platform`. Separately assert
that `pyproject.toml` contains neither `platform/wanwu` nor `platform.wanwu`.

- [ ] **Step 4: Run the boundary file**

Run `python -m pytest tests/test_pami_boundary.py -v`.

Expected: 5 passed. These tests characterize and lock the already approved
boundary; they do not introduce real pami behavior.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_pami_boundary.py
git commit -m "test: enforce zhiyin wanwu integration boundary"
```

---

### Task 4: Align CI and Documentation

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/superpowers/plans/2026-09-15-pami-wanwu-source-deployment-baseline.md`

- [ ] **Step 1: Extend the CI zhiyinbase step**

Run the vendor, container, deployment, route, and pami-boundary test files, then
run `python scripts/verify_wanwu_routes.py` from the repository root.

- [ ] **Step 2: Correct the README scope**

State that:

- the current delivery contains the source snapshot, independent build, unified
  Compose, and native route configuration;
- native routes use `http://127.0.0.1:8081` and zhiyinbase authentication;
- Zhiyin `/api/v1/*` does not proxy them;
- pami switches remain off and real resources are not claimed as connected.

- [ ] **Step 3: Link plans and mark the retained baseline**

Add this plan to `docs/README.md`. Add a status note to the earlier baseline plan
that it represents stages 1–2 and that zhiyinbase is not re-imported.

- [ ] **Step 4: Run focused verification**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py tests/test_pami_boundary.py tests/test_docs_alignment.py -q
python ../../scripts/verify_wanwu_routes.py
```

Expected: zero failures and route verifier exit 0.

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/ci.yml README.md docs/README.md docs/superpowers/plans
git commit -m "docs: finalize embedded wanwu delivery scope"
```

---

### Task 5: Complete Acceptance

**Files:** Verify only.

- [ ] **Step 1: Run backend verification**

```powershell
Set-Location zhiyin-src/template
python -m pytest -q
python -m ruff check . ../../scripts
python scripts/export_openapi.py --check
python -m zhiyin_boot --check --phase=1
```

Expected: zero failures and phase-one `passed: true`.

- [ ] **Step 2: Run frontend verification**

```powershell
Set-Location zhiyin-web
npm ci --no-audit --no-fund
npm run typecheck
npm run check:api
```

Expected: all commands exit zero and generated API types have no semantic diff.

- [ ] **Step 3: Render deployment configuration**

```powershell
Set-Location ../../..
python deploy/init_env.py
docker compose --project-directory platform/wanwu --env-file deploy/.env -f platform/wanwu/docker-compose.yaml -f deploy/compose.yaml config --quiet
```

Expected: exit zero.

- [ ] **Step 4: Verify provenance and repository state**

```powershell
git diff --check
git ls-files platform/wanwu/.env platform/wanwu/.env.bak deploy/.env
git status --short
git log -8 --oneline --decorate
```

Expected: no whitespace errors, no tracked secret files, and a clean worktree with
focused route, boundary, and documentation commits.

- [ ] **Step 5: Record the scoped conclusion**

Report that source, independent build assets, unified deployment configuration,
native route exposure, boundary guards, CI, and documentation are complete.
Explicitly state that real zhiyinbase accounts, models, resources, and business
requests were not configured or validated.
