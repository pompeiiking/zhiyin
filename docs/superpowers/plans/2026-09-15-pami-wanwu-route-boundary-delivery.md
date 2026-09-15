# pami/Wanwu Route and Boundary Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete stages 3–5 of the approved Wanwu source-and-interface exposure design while preserving the already imported source snapshot and unified deployment baseline.

**Architecture:** Wanwu remains an independent platform under `platform/wanwu`; its own Nginx/BFF exposes native routes. Zhiyin keeps its `/api/v1/*` product API and disabled pami adapter skeletons, with automated contracts preventing cross-layer imports or accidental claims of real integration.

**Tech Stack:** Python 3.10+, pytest, JSON, Nginx configuration, Docker Compose, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-09-15-pami-wanwu-integration-design.md`

## Global Constraints

- Do not re-import `platform/wanwu` unless the approved upstream revision changes.
- Keep the imported revision `969a74c7c376169d2a88c72891807d35bb40861b`.
- Do not add a Wanwu proxy route to `zhiyin-api`.
- Do not implement real pami HTTP calls or enable `ZHIYIN_USE_PAMI_*`.
- Keep Wanwu authentication, organization, permission, API Key, and callback behavior unchanged.
- Keep Wanwu internal service ports removed by the Compose override.
- Treat route presence as configuration evidence only, not proof of a successful business request.
- Preserve existing Zhiyin architecture, contract, lint, OpenAPI, and phase-one checks.

## Current Baseline

Stages 1 and 2 already exist on `feature/pami-wanwu-baseline`:

- reproducible importer: `scripts/import_wanwu.py`;
- imported source and provenance: `platform/wanwu/.zhiyin-vendor.json`, `platform/wanwu/UPSTREAM.md`;
- Zhiyin container: `zhiyin-src/template/Dockerfile`;
- unified deployment assets: `deploy/compose.yaml`, `deploy/init_env.py`, lifecycle scripts;
- CI checks for source, container, and Compose assets.

This plan audits that baseline but does not recreate it.

## File Map

| File | Responsibility |
| --- | --- |
| `deploy/wanwu-routes.json` | Checked-in contract for native Wanwu route prefixes, targets, and trust surfaces |
| `zhiyin-src/template/tests/test_wanwu_routes.py` | Verifies route contract against Nginx, Compose, and interface documentation |
| `zhiyin-src/template/tests/test_pami_boundary.py` | Locks disabled pami defaults, explicit skeleton failure, and package/import boundaries |
| `.github/workflows/ci.yml` | Runs route and boundary checks in CI |
| `README.md` | States the actual delivered scope and native Wanwu entrypoint |
| `docs/README.md` | Links the approved design and this completion plan |
| `docs/superpowers/plans/2026-09-15-pami-wanwu-source-deployment-baseline.md` | Marks the earlier plan as the completed stages 1–2 baseline |

---

### Task 1: Lock the Wanwu Native Route Contract

**Files:**
- Create: `deploy/wanwu-routes.json`
- Create: `zhiyin-src/template/tests/test_wanwu_routes.py`

**Interfaces:**
- Consumes: `platform/wanwu/configs/middleware/nginx/conf.d/aibase.conf`
- Consumes: `deploy/compose.yaml`
- Consumes: `docs/技术架构文档/外部平台/pami-Wanwu/接口.md`
- Produces: a machine-readable list of native route prefixes and upstream targets

- [ ] **Step 1: Write the failing manifest-presence test**

Create `zhiyin-src/template/tests/test_wanwu_routes.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_MANIFEST = REPO_ROOT / "deploy" / "wanwu-routes.json"
NGINX_CONFIG = (
    REPO_ROOT
    / "platform"
    / "wanwu"
    / "configs"
    / "middleware"
    / "nginx"
    / "conf.d"
    / "aibase.conf"
)
COMPOSE_OVERRIDE = REPO_ROOT / "deploy" / "compose.yaml"
INTERFACE_DOC = (
    REPO_ROOT
    / "docs"
    / "技术架构文档"
    / "外部平台"
    / "pami-Wanwu"
    / "接口.md"
)
ROUTING_DOC = (
    REPO_ROOT
    / "docs"
    / "技术架构文档"
    / "外部平台"
    / "pami-Wanwu"
    / "架构文档"
    / "08-接口与通信架构.md"
)


def _routes() -> list[dict[str, str]]:
    payload = json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))
    return payload["routes"]


def _location_block(config: str, prefix: str) -> str:
    pattern = rf"location\s+\^~\s+{re.escape(prefix)}\s*\{{(?P<body>.*?)\n\s*\}}"
    match = re.search(pattern, config, flags=re.DOTALL)
    assert match is not None, f"missing nginx location for {prefix}"
    return match.group("body")


def test_route_manifest_exists_and_has_all_native_entrypoints() -> None:
    assert ROUTE_MANIFEST.is_file()
    assert {route["prefix"] for route in _routes()} == {
        "/user/api/",
        "/use/model/api/",
        "/service/api/",
        "/workflow/api/",
        "/minio/download/api/",
    }
```

- [ ] **Step 2: Run the test and confirm the manifest is missing**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py::test_route_manifest_exists_and_has_all_native_entrypoints -v
```

Expected: FAIL because `deploy/wanwu-routes.json` does not exist.

- [ ] **Step 3: Add the route manifest**

Create `deploy/wanwu-routes.json`:

```json
{
  "entrypoint": "wanwu-nginx",
  "local_url": "http://127.0.0.1:8081",
  "claim": "route-configured",
  "routes": [
    {
      "prefix": "/user/api/",
      "upstream": "http://bff-service:6668/",
      "trust_surface": "wanwu-jwt-and-permissions"
    },
    {
      "prefix": "/use/model/api/",
      "upstream": "http://bff-service:6668/",
      "trust_surface": "wanwu-model-middleware"
    },
    {
      "prefix": "/service/api/",
      "upstream": "http://bff-service:6668/",
      "trust_surface": "per-route-jwt-api-key-or-open-rule"
    },
    {
      "prefix": "/workflow/api/",
      "upstream": "http://agentscope-wanwu:6672/",
      "trust_surface": "wanwu-workflow-protocol"
    },
    {
      "prefix": "/minio/download/api/",
      "upstream": "http://minio-wanwu:9000/",
      "trust_surface": "wanwu-minio-download-rule"
    }
  ]
}
```

- [ ] **Step 4: Verify the manifest test passes**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py::test_route_manifest_exists_and_has_all_native_entrypoints -v
```

Expected: PASS.

- [ ] **Step 5: Add Nginx and Compose assertions**

Append to `test_wanwu_routes.py`:

```python
def test_each_manifest_route_matches_the_wanwu_nginx_upstream() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    for route in _routes():
        block = _location_block(config, route["prefix"])
        assert f'proxy_pass       {route["upstream"]}' in block or (
            f'proxy_pass      {route["upstream"]}' in block
        )


def test_only_wanwu_nginx_is_bound_to_the_host() -> None:
    compose = COMPOSE_OVERRIDE.read_text(encoding="utf-8")
    for service in (
        "mysql",
        "redis",
        "minio",
        "kafka",
        "es",
        "bff-service",
        "agentscope",
        "rag",
        "agent",
    ):
        assert f"  {service}:\n    ports: !reset []" in compose
    assert '"127.0.0.1:8081:8081"' in compose
```

- [ ] **Step 6: Verify the Nginx and Compose assertions**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit the route contract**

```powershell
git add deploy/wanwu-routes.json zhiyin-src/template/tests/test_wanwu_routes.py
git commit -m "test: lock wanwu native route exposure"
```

---

### Task 2: Cross-check the Route Contract Against Platform Documentation

**Files:**
- Modify: `zhiyin-src/template/tests/test_wanwu_routes.py`

**Interfaces:**
- Consumes: route manifest from Task 1
- Produces: a guard against claiming undocumented route families

- [ ] **Step 1: Write the failing documentation cross-check**

Append:

```python
def test_route_contract_is_anchored_in_platform_documentation() -> None:
    documentation = (
        INTERFACE_DOC.read_text(encoding="utf-8")
        + "\n"
        + ROUTING_DOC.read_text(encoding="utf-8")
    )
    documented_anchors = {
        "/user/api/": "/user/api/v1/",
        "/use/model/api/": "/use/model/api/",
        "/service/api/": "/service/api/openapi/v1/",
        "/workflow/api/": "/workflow/api/",
        "/minio/download/api/": "/minio/download/api/",
    }
    for route in _routes():
        assert documented_anchors[route["prefix"]] in documentation
```

- [ ] **Step 2: Run the cross-check**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py::test_route_contract_is_anchored_in_platform_documentation -v
```

Expected: PASS because method-level interfaces are recorded in `接口.md` and the
MinIO download route is recorded in `08-接口与通信架构.md`.

- [ ] **Step 3: Run the full route test**

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit the documentation contract**

```powershell
git add zhiyin-src/template/tests/test_wanwu_routes.py
git commit -m "docs: align wanwu routes with interface catalog"
```

---

### Task 3: Lock the Zhiyin/Pami Boundary

**Files:**
- Create: `zhiyin-src/template/tests/test_pami_boundary.py`

**Interfaces:**
- Consumes: `zhiyin_boot.settings.Settings`
- Consumes: existing skeleton adapters in `zhiyin_infrastructure.pami.adapters`
- Produces: executable evidence that the current task does not enable or implement real pami integration

- [ ] **Step 1: Add default-setting and package-boundary tests**

Create:

```python
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from zhiyin_boot.settings import Settings
from zhiyin_infrastructure.pami.adapters import PamiAuthGateway, PamiSearchGateway


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TEMPLATE_ROOT.parents[1]


def test_pami_adapters_are_disabled_by_default() -> None:
    settings = Settings()
    assert settings.use_pami_llm is False
    assert settings.use_pami_knowledge is False
    assert settings.use_pami_auth is False


def test_wanwu_is_not_a_zhiyin_python_package() -> None:
    pyproject = (TEMPLATE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "platform/wanwu" not in pyproject
    assert "platform.wanwu" not in pyproject


def test_zhiyin_packages_do_not_import_wanwu_source() -> None:
    roots = (
        "zhiyin-api",
        "zhiyin-business",
        "zhiyin-orchestration",
        "zhiyin-data-sdk",
        "zhiyin-infrastructure",
        "zhiyin-boot",
    )
    violations: list[str] = []
    for root_name in roots:
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
```

- [ ] **Step 2: Run the boundary tests**

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_pami_boundary.py -v
```

Expected: PASS. These are characterization tests for already approved architecture.

- [ ] **Step 3: Add explicit-failure tests for disabled skeleton behavior**

Append:

```python
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
```

- [ ] **Step 4: Run the complete boundary test**

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_pami_boundary.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit the boundary guard**

```powershell
git add zhiyin-src/template/tests/test_pami_boundary.py
git commit -m "test: enforce zhiyin wanwu integration boundary"
```

---

### Task 4: Align CI and Operator Documentation

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/superpowers/plans/2026-09-15-pami-wanwu-source-deployment-baseline.md`

**Interfaces:**
- Consumes: tests from Tasks 1–3
- Produces: accurate CI coverage and user-facing completion language

- [ ] **Step 1: Add the new contracts to CI**

Change the Wanwu test step to:

```yaml
      - name: Wanwu 源码、路由与架构边界
        run: >-
          python -m pytest
          tests/test_wanwu_vendor.py
          tests/test_container_assets.py
          tests/test_deploy_assets.py
          tests/test_wanwu_routes.py
          tests/test_pami_boundary.py
          -q
```

- [ ] **Step 2: Correct the repository scope statement**

Replace the final paragraph under `README.md` “内置 pami/Wanwu 部署基线” with:

```markdown
当前交付包含 Wanwu 源码快照、独立构建、统一 Compose 和原生接口路由。
Wanwu 原生接口从 `http://127.0.0.1:8081` 的 Nginx/BFF 入口访问，继续使用
Wanwu 自身的 JWT、API Key 和权限规则。职引 `/api/v1/*` 不透明代理这些接口。

`ZHIYIN_USE_PAMI_*` 保持关闭，`zhiyin-infrastructure/pami/` 仅保留生产替换
骨架；本交付不宣称真实账号、模型、知识库、Agent、RAG 或工作流已经联通。
```

- [ ] **Step 3: Mark the earlier implementation plan as the completed baseline**

After the header of
`docs/superpowers/plans/2026-09-15-pami-wanwu-source-deployment-baseline.md`,
add:

```markdown
> **状态说明（2026-09-15）：** 本计划对应现行设计的阶段 1–2，源码快照与部署
> 资产已经提交。后续路由、边界、CI 与文档收口由
> `2026-09-15-pami-wanwu-route-boundary-delivery.md` 承接；不重新导入 Wanwu。
```

- [ ] **Step 4: Link the completion plan in the document index**

Add below the existing baseline-plan row in `docs/README.md`:

```markdown
| [superpowers/plans/2026-09-15-pami-wanwu-route-boundary-delivery.md](superpowers/plans/2026-09-15-pami-wanwu-route-boundary-delivery.md) | pami/Wanwu 原生路由、职引边界与最终验收计划 |
```

- [ ] **Step 5: Run focused tests and documentation checks**

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_routes.py tests/test_pami_boundary.py tests/test_docs_alignment.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit CI and documentation**

```powershell
git add .github/workflows/ci.yml README.md docs/README.md docs/superpowers/plans
git commit -m "docs: finalize embedded wanwu delivery scope"
```

---

### Task 5: Complete Static Acceptance

**Files:**
- Verify only

**Interfaces:**
- Consumes: all artifacts from Tasks 1–4
- Produces: final evidence against the approved design

- [ ] **Step 1: Run the backend suite**

```powershell
Set-Location zhiyin-src/template
python -m pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Run lint, OpenAPI, and assembly checks**

```powershell
python -m ruff check . ../../scripts/import_wanwu.py
python scripts/export_openapi.py --check
python -m zhiyin_boot --check --phase=1
```

Expected: all commands exit zero; the phase-one gate reports `passed: true`.

- [ ] **Step 3: Run frontend checks**

```powershell
Set-Location zhiyin-web
npm ci --no-audit --no-fund
npm run typecheck
npm run check:api
```

Expected: typecheck passes and generated API types have no semantic diff.

- [ ] **Step 4: Render the unified Compose model**

```powershell
Set-Location ../../..
python deploy/init_env.py
docker compose --project-directory platform/wanwu --env-file deploy/.env -f platform/wanwu/docker-compose.yaml -f deploy/compose.yaml config --quiet
```

Expected: Compose exits zero.

- [ ] **Step 5: Verify provenance, secrets, and cleanliness**

```powershell
git diff --check
git ls-files platform/wanwu/.env platform/wanwu/.env.bak deploy/.env
git status --short
git log -8 --oneline --decorate
```

Expected:

- `git diff --check` prints nothing;
- the secret-file query prints nothing;
- the worktree is clean;
- focused commits for routes, boundary guards, and documentation are present.

- [ ] **Step 6: Record the completion statement**

Use this exact scope:

```text
Wanwu source, independent build assets, unified Compose configuration, native
Nginx/BFF route exposure, Zhiyin boundary guards, CI, and operator documentation
are complete. Real Wanwu accounts, models, resources, and business requests were
not configured or validated and are outside this delivery.
```
