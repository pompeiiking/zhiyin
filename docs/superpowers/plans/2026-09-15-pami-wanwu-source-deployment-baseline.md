# pami/Wanwu Source and Deployment Baseline Implementation Plan

> **状态说明（2026-09-15）：** 本计划对应现行设计的阶段 1–2，源码快照与部署
> 资产已经提交。后续路由、边界、CI 与文档收口由
> `2026-09-15-pami-wanwu-route-boundary-delivery.md` 承接；不重新导入 Wanwu。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import a clean, traceable Wanwu source snapshot into the zhiyin repository and provide a repeatable container build and unified Compose baseline that starts Wanwu and the zhiyin backend on one internal network.

**Architecture:** Wanwu remains an independently built platform under `platform/wanwu`; the zhiyin Python packages never import it. A cross-platform import tool records provenance and filters sensitive runtime files. The deployment layer applies a security override to Wanwu's Compose model and adds a containerized `zhiyin-api`, with stateful and engine services reachable only through the shared internal network.

**Tech Stack:** Python 3.11, pytest, Git archive, Docker Engine, Docker Compose v2.24+, FastAPI/Uvicorn, Wanwu Go/Python/Vue containers.

**Spec:** `docs/superpowers/specs/2026-09-15-pami-wanwu-integration-design.md`

## Global Constraints

- This plan implements only design Phase 1: source and deployment baseline. It does not implement pami runtime or control-plane adapters.
- Import Wanwu commit `969a74c7c376169d2a88c72891807d35bb40861b` from `D:/kaixuexiangmu/ceshi/wanwu` as the initial baseline.
- Import committed content only. Leave all uncommitted source-worktree changes untouched and outside the snapshot until they receive a separate patch review.
- Exclude `.git`, `.env.bak`, `.env.image.amd64`, `.env.image.arm64`, logs, PID files, caches, generated output, and local test state.
- Preserve Wanwu's Apache 2.0 `LICENSE` and record the source revision and remote URL in a machine-readable manifest and `UPSTREAM.md`.
- `platform/wanwu` is not a Python package and must not be added to `pyproject.toml`.
- The zhiyin backend must run as a non-root container user and expose only port `8000` inside the Compose network.
- Wanwu's Nginx is the only Wanwu HTTP entry used by later adapters; individual Wanwu microservice ports remain internal.
- Secrets are generated into ignored `deploy/.env`; they are not committed to source control or printed by verification scripts.
- Existing architecture, contract, lint, OpenAPI, and phase-one checks must remain green.

## File Map

| File | Responsibility |
| --- | --- |
| `scripts/import_wanwu.py` | Export one committed Wanwu revision, reject unsafe destinations, filter forbidden files, and write provenance |
| `zhiyin-src/template/tests/test_wanwu_vendor.py` | Test importer safety and assert that the checked-in snapshot is complete and sanitized |
| `platform/wanwu/**` | Imported Wanwu source snapshot |
| `platform/wanwu/.zhiyin-vendor.json` | Machine-readable revision, remote, import date, and exclusion record |
| `platform/wanwu/UPSTREAM.md` | Human-readable provenance and update policy |
| `zhiyin-src/template/Dockerfile` | Production-like zhiyin backend image |
| `zhiyin-src/template/.dockerignore` | Small, secret-free backend build context |
| `zhiyin-src/template/tests/test_container_assets.py` | Static container contract tests |
| `deploy/compose.yaml` | Override Wanwu host ports and add the zhiyin backend service |
| `deploy/.env.example` | Non-secret deployment defaults and empty secret slots |
| `deploy/init_env.py` | Create `deploy/.env` with generated local secrets |
| `deploy/up.ps1` | Validate environment/network and start the unified stack |
| `deploy/down.ps1` | Stop the unified stack without deleting data volumes |
| `deploy/verify.ps1` | Render Compose config and check business-level readiness |
| `zhiyin-src/template/tests/test_deploy_assets.py` | Static deployment contract tests |
| `.github/workflows/ci.yml` | Verify vendor boundary, backend image, and rendered Compose model |
| `README.md` | Document one-command local deployment and current phase boundary |

---

### Task 1: Safe and Reproducible Wanwu Importer

**Files:**
- Create: `scripts/import_wanwu.py`
- Create: `zhiyin-src/template/tests/test_wanwu_vendor.py`

**Interfaces:**
- Consumes: a local Git repository path, a full revision hash, and a destination path.
- Produces: `import_snapshot(source: Path, destination: Path, revision: str) -> dict[str, object]` and a sanitized source tree containing `.zhiyin-vendor.json` and `UPSTREAM.md`.

- [ ] **Step 1: Write importer unit tests**

Create `zhiyin-src/template/tests/test_wanwu_vendor.py`. Load the root script with `importlib.util`, initialize a temporary Git repository, commit representative text, binary, license, and forbidden environment files, and assert:

```python
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
IMPORTER_PATH = REPO_ROOT / "scripts" / "import_wanwu.py"
VENDOR_ROOT = REPO_ROOT / "platform" / "wanwu"


def load_importer():
    spec = importlib.util.spec_from_file_location("import_wanwu", IMPORTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=Vendor Test", "-c", "user.email=vendor@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_import_snapshot_filters_sensitive_files_and_records_revision(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init")
    (source / "LICENSE").write_text("Apache License 2.0", encoding="utf-8")
    (source / "README.md").write_text("wanwu", encoding="utf-8")
    (source / ".env.bak").write_text("PASSWORD=secret", encoding="utf-8")
    (source / "asset.bin").write_bytes(b"\x00\x01")
    git(source, "add", ".")
    git(source, "commit", "-m", "fixture")
    revision = git(source, "rev-parse", "HEAD")

    destination = tmp_path / "workspace" / "platform" / "wanwu"
    destination.parent.mkdir(parents=True)
    manifest = load_importer().import_snapshot(source, destination, revision)

    assert (destination / "README.md").read_text(encoding="utf-8") == "wanwu"
    assert (destination / "asset.bin").read_bytes() == b"\x00\x01"
    assert not (destination / ".env.bak").exists()
    assert manifest["revision"] == revision
    assert json.loads((destination / ".zhiyin-vendor.json").read_text(encoding="utf-8"))["revision"] == revision


def test_import_snapshot_refuses_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "platform" / "wanwu"
    destination.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        load_importer().import_snapshot(tmp_path, destination, "0" * 40)


def test_checked_in_wanwu_snapshot_is_sanitized() -> None:
    assert (VENDOR_ROOT / "LICENSE").is_file()
    assert (VENDOR_ROOT / "go.mod").is_file()
    assert (VENDOR_ROOT / "docker-compose.yaml").is_file()
    manifest = json.loads((VENDOR_ROOT / ".zhiyin-vendor.json").read_text(encoding="utf-8"))
    assert manifest["revision"] == "969a74c7c376169d2a88c72891807d35bb40861b"
    forbidden = [
        VENDOR_ROOT / ".env.bak",
        VENDOR_ROOT / ".env.image.amd64",
        VENDOR_ROOT / ".env.image.arm64",
        VENDOR_ROOT / ".git",
    ]
    assert not [path for path in forbidden if path.exists()]
    assert not list(VENDOR_ROOT.rglob("*.log"))
    assert not list(VENDOR_ROOT.rglob("*.pid"))
```

- [ ] **Step 2: Run tests and confirm the importer is missing**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_vendor.py -v
```

Expected: the importer tests fail because `scripts/import_wanwu.py` and `platform/wanwu` do not exist.

- [ ] **Step 3: Implement the importer**

Create `scripts/import_wanwu.py` with these exact behaviors:

```python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Sequence

BLOCKED_ROOT_FILES = frozenset({".env.bak", ".env.image.amd64", ".env.image.arm64"})
BLOCKED_SUFFIXES = frozenset({".log", ".pid"})
BLOCKED_PARTS = frozenset({".git", ".cache", "output", "__pycache__"})


def run_git(source: Path, args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={source.as_posix()}", "-C", str(source), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def is_blocked(relative: Path) -> bool:
    return (
        relative.as_posix() in BLOCKED_ROOT_FILES
        or relative.suffix.lower() in BLOCKED_SUFFIXES
        or any(part in BLOCKED_PARTS for part in relative.parts)
    )


def import_snapshot(source: Path, destination: Path, revision: str) -> dict[str, object]:
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=False)
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")

    resolved_revision = run_git(source, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
    if resolved_revision != revision:
        raise ValueError("revision must be a full 40-character commit hash")
    remote = run_git(source, ["remote", "get-url", "origin"]) if run_git(source, ["remote"]) else "local"

    with tempfile.TemporaryDirectory(prefix="zhiyin-wanwu-import-") as temp_name:
        temp = Path(temp_name)
        archive = temp / "wanwu.zip"
        extracted = temp / "source"
        subprocess.run(
            ["git", "-c", f"safe.directory={source.as_posix()}", "-C", str(source), "archive", "--format=zip", f"--output={archive}", revision],
            check=True,
        )
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(extracted)

        for path in sorted(extracted.rglob("*"), reverse=True):
            relative = path.relative_to(extracted)
            if not is_blocked(relative):
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

        manifest: dict[str, object] = {
            "name": "wanwu",
            "revision": resolved_revision,
            "remote": remote,
            "imported_on": date.today().isoformat(),
            "excluded": sorted(BLOCKED_ROOT_FILES | BLOCKED_PARTS | {"*.log", "*.pid"}),
        }
        (extracted / ".zhiyin-vendor.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (extracted / "UPSTREAM.md").write_text(
            "# Wanwu upstream\n\n"
            f"- Remote: `{remote}`\n"
            f"- Revision: `{resolved_revision}`\n"
            f"- Imported: `{manifest['imported_on']}`\n\n"
            "This directory is a committed source snapshot. Update it only through "
            "`scripts/import_wanwu.py` and review local patches separately.\n",
            encoding="utf-8",
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extracted), str(destination))
    return manifest


def validate_cli_destination(destination: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    expected = (repository_root / "platform" / "wanwu").resolve(strict=False)
    if destination.resolve(strict=False) != expected:
        raise ValueError(f"destination must be {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    validate_cli_destination(args.destination)
    print(json.dumps(import_snapshot(args.source, args.destination, args.revision), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the isolated importer tests**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_vendor.py::test_import_snapshot_filters_sensitive_files_and_records_revision tests/test_wanwu_vendor.py::test_import_snapshot_refuses_existing_destination -v
```

Expected: both isolated tests pass; the checked-in snapshot test still fails because the real snapshot has not been imported.

- [ ] **Step 5: Commit the importer and tests**

```powershell
git add scripts/import_wanwu.py zhiyin-src/template/tests/test_wanwu_vendor.py
git commit -m "build: add reproducible wanwu source importer"
```

---

### Task 2: Import and Verify the Wanwu Source Snapshot

**Files:**
- Create: `platform/wanwu/**`
- Create: `platform/wanwu/.zhiyin-vendor.json`
- Create: `platform/wanwu/UPSTREAM.md`
- Modify: `.gitignore`
- Test: `zhiyin-src/template/tests/test_wanwu_vendor.py`

**Interfaces:**
- Consumes: `scripts/import_wanwu.py::import_snapshot` from Task 1 and committed source revision `969a74c7c376169d2a88c72891807d35bb40861b`.
- Produces: a sanitized, buildable Wanwu tree at `platform/wanwu` with immutable provenance.

- [ ] **Step 1: Confirm the source revision without touching its dirty worktree**

Run:

```powershell
git -c safe.directory='D:/kaixuexiangmu/ceshi/wanwu' -C 'D:/kaixuexiangmu/ceshi/wanwu' rev-parse HEAD
git -c safe.directory='D:/kaixuexiangmu/ceshi/wanwu' -C 'D:/kaixuexiangmu/ceshi/wanwu' status --short
```

Expected: the first command prints `969a74c7c376169d2a88c72891807d35bb40861b`. The second command may list local changes; the importer does not include or modify them.

- [ ] **Step 2: Import the committed snapshot**

Run from the zhiyin repository root:

```powershell
python scripts/import_wanwu.py --source 'D:/kaixuexiangmu/ceshi/wanwu' --destination 'platform/wanwu' --revision '969a74c7c376169d2a88c72891807d35bb40861b'
```

Expected: JSON output contains the exact revision and `platform/wanwu` is created.

- [ ] **Step 3: Add vendor-local runtime exclusions**

Append these entries to `.gitignore`:

```gitignore

# ---- Embedded Wanwu runtime state ----
platform/wanwu/.env
platform/wanwu/.env.*
platform/wanwu/.cache/
platform/wanwu/output/
platform/wanwu/runtime/
platform/wanwu/**/*.log
platform/wanwu/**/*.pid
deploy/.env
```

The importer's explicitly created `platform/wanwu/.zhiyin-vendor.json` remains tracked.

- [ ] **Step 4: Run snapshot and architecture checks**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_wanwu_vendor.py tests/test_architecture.py tests/test_docs_alignment.py -v
python -m ruff check ../../scripts/import_wanwu.py tests/test_wanwu_vendor.py
```

Expected: all tests and lint checks pass. `platform/wanwu` must not appear in the AST package map.

- [ ] **Step 5: Inspect exactly what will be committed**

Run from repository root:

```powershell
git status --short
git diff -- .gitignore
git status --short --ignored platform/wanwu | Select-String -Pattern '\.env|\.log|\.pid|\.cache|output'
```

Expected: source files, `LICENSE`, provenance files, and `.gitignore` are visible; forbidden runtime files are absent or ignored.

- [ ] **Step 6: Commit the source snapshot**

```powershell
git add .gitignore platform/wanwu
git commit -m "vendor: import wanwu platform source baseline"
```

---

### Task 3: Containerize the zhiyin Backend

**Files:**
- Create: `zhiyin-src/template/Dockerfile`
- Create: `zhiyin-src/template/.dockerignore`
- Create: `zhiyin-src/template/tests/test_container_assets.py`

**Interfaces:**
- Consumes: the existing `python -m zhiyin_boot --host 0.0.0.0 --port 8000` entry point and `/healthz` endpoint.
- Produces: image `zhiyin/backend:dev`, internal port `8000`, and a Docker health status based on `/healthz`.

- [ ] **Step 1: Write the container contract tests**

Create `zhiyin-src/template/tests/test_container_assets.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backend_dockerfile_runs_as_non_root_and_uses_healthz() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.11-slim" in text
    assert "USER zhiyin" in text
    assert '"--host", "0.0.0.0"' in text
    assert "/healthz" in text
    assert 'CMD ["python", "-m", "zhiyin_boot"' in text


def test_dockerignore_excludes_secrets_and_generated_files() -> None:
    lines = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())
    assert {".env", ".env.*", ".git", ".venv", "**/__pycache__", "zhiyin-web/node_modules"} <= lines
```

- [ ] **Step 2: Run the tests and confirm missing assets**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_container_assets.py -v
```

Expected: failures report missing `Dockerfile` and `.dockerignore`.

- [ ] **Step 3: Create the backend Dockerfile**

Create `zhiyin-src/template/Dockerfile`:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system zhiyin && useradd --system --gid zhiyin --home-dir /app zhiyin

COPY pyproject.toml README.md ./
COPY zhiyin-kernel ./zhiyin-kernel
COPY zhiyin-api ./zhiyin-api
COPY zhiyin-business ./zhiyin-business
COPY zhiyin-orchestration ./zhiyin-orchestration
COPY zhiyin-data-sdk ./zhiyin-data-sdk
COPY zhiyin-infrastructure ./zhiyin-infrastructure
COPY zhiyin-boot ./zhiyin-boot
COPY data ./data

RUN python -m pip install . && chown -R zhiyin:zhiyin /app

USER zhiyin
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["python", "-m", "zhiyin_boot", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create the backend build exclusions**

Create `zhiyin-src/template/.dockerignore`:

```dockerignore
.git
.env
.env.*
.venv
**/__pycache__
**/*.pyc
.pytest_cache
.ruff_cache
build
dist
*.egg-info
tests
contracts
scripts
zhiyin-web/node_modules
zhiyin-web/dist
data/objects
data/cache
data/logs
```

- [ ] **Step 5: Run static tests and build the image**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_container_assets.py tests/test_app.py -v
docker build --tag zhiyin/backend:dev .
docker run --rm zhiyin/backend:dev python -m zhiyin_boot --check --phase=1
```

Expected: tests pass, the image builds, and the containerized phase-one gate exits zero.

- [ ] **Step 6: Commit the backend image assets**

```powershell
git add zhiyin-src/template/Dockerfile zhiyin-src/template/.dockerignore zhiyin-src/template/tests/test_container_assets.py
git commit -m "build: containerize zhiyin backend"
```

---

### Task 4: Unified Wanwu and zhiyin Compose Baseline

**Files:**
- Create: `deploy/compose.yaml`
- Create: `deploy/.env.example`
- Create: `deploy/init_env.py`
- Create: `deploy/up.ps1`
- Create: `deploy/down.ps1`
- Create: `deploy/verify.ps1`
- Create: `zhiyin-src/template/tests/test_deploy_assets.py`

**Interfaces:**
- Consumes: `platform/wanwu/docker-compose.yaml`, `zhiyin-src/template/Dockerfile`, Docker Compose v2.24+, and external network `wanwu-net`.
- Produces: `python deploy/init_env.py`, `pwsh deploy/up.ps1`, `pwsh deploy/verify.ps1`, and `pwsh deploy/down.ps1` as the deployment lifecycle.

- [ ] **Step 1: Write deployment asset tests**

Create `zhiyin-src/template/tests/test_deploy_assets.py`:

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY = REPO_ROOT / "deploy"


def test_compose_includes_wanwu_and_keeps_zhiyin_internal() -> None:
    text = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
    assert "zhiyin-api:" in text
    assert "expose:" in text and '"8000"' in text
    assert "wanwu-net" in text
    assert "condition: service_healthy" in text
    for service in ("mysql", "redis", "minio", "kafka", "es", "bff-service", "agentscope", "rag", "agent"):
        assert f"  {service}:\n    ports: !reset []" in text
    assert '"127.0.0.1:8081:8081"' in text


def test_env_example_has_no_committed_secrets() -> None:
    text = (DEPLOY / ".env.example").read_text(encoding="utf-8")
    for key in (
        "WANWU_MYSQL_PASSWORD",
        "WANWU_REDIS_PASSWORD",
        "WANWU_MINIO_PASSWORD",
        "WANWU_ELASTIC_PASSWORD",
    ):
        assert f"{key}=\n" in text


def test_lifecycle_scripts_do_not_delete_volumes() -> None:
    down = (DEPLOY / "down.ps1").read_text(encoding="utf-8")
    assert " down" in down
    assert "--volumes" not in down
    assert " -v" not in down
```

- [ ] **Step 2: Run tests and confirm deployment assets are missing**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_deploy_assets.py -v
```

Expected: tests fail because the deployment files do not exist.

- [ ] **Step 3: Create the unified Compose model**

Create `deploy/compose.yaml`:

```yaml
name: zhiyin

services:
  mysql:
    ports: !reset []
  redis:
    ports: !reset []
  minio:
    ports: !reset []
  kafka:
    ports: !reset []
  es:
    ports: !reset []
  bff-service:
    ports: !reset []
  agentscope:
    ports: !reset []
  rag:
    ports: !reset []
  agent:
    ports: !reset []
  nginx:
    ports: !override
      - "127.0.0.1:8081:8081"

  zhiyin-api:
    build:
      context: ../zhiyin-src/template
      dockerfile: Dockerfile
    image: zhiyin/backend:dev
    restart: unless-stopped
    env_file:
      - .env
    environment:
      ZHIYIN_ENV: local
      ZHIYIN_PAMI_BASE_URL: http://nginx:8081
    expose:
      - "8000"
    networks:
      - wanwu-net
    depends_on:
      nginx:
        condition: service_healthy
```

Do not enable `ZHIYIN_USE_PAMI_*` in Phase 1 because the current adapters still raise `NotImplementedError`.

- [ ] **Step 4: Create non-secret environment defaults**

Create `deploy/.env.example` with the public image and topology values below, followed by empty secret values:

```dotenv
WANWU_ARCH=amd64
WANWU_PROJECT_DIR=./platform/wanwu/runtime
WANWU_EXTERNAL_IP=127.0.0.1
WANWU_EXTERNAL_PORT=8081
WANWU_WEB_BASE_URL=http://127.0.0.1:8081
WANWU_API_BASE_URL=http://nginx:8081
WANWU_VERSION=embedded-969a74c
WANWU_DOCKER_NETWORK=wanwu-net
WANWU_DB_NAME=wanwu
WANWU_MYSQL_HOST=mysql-wanwu
WANWU_MYSQL_PORT=3306
WANWU_MYSQL_ADDRESS=mysql-wanwu:3306
WANWU_MYSQL_USER=wanwu
WANWU_MYSQL_PASSWORD=
WANWU_REDIS_HOST=redis-wanwu
WANWU_REDIS_PORT=6379
WANWU_REDIS_ADDRESS=redis-wanwu:6379
WANWU_REDIS_PASSWORD=
WANWU_MINIO_HOST=minio-wanwu
WANWU_MINIO_PORT=9000
WANWU_MINIO_ENDPOINT=minio-wanwu:9000
WANWU_MINIO_USER=wanwu
WANWU_MINIO_PASSWORD=
WANWU_KAFKA_HOST=kafka-wanwu
WANWU_KAFKA_PORT=9092
WANWU_KAFKA_ADDRESS=kafka-wanwu:9092
WANWU_KAFKA_USER=wanwu
WANWU_KAFKA_PASSWORD=
WANWU_ELASTIC_HOST=es-wanwu
WANWU_ELASTIC_PORT=9200
WANWU_ELASTIC_ADDRESS=http://es-wanwu:9200
WANWU_ELASTIC_USER=elastic
WANWU_ELASTIC_PASSWORD=
WANWU_KIBANA_HOST=kibana-wanwu
WANWU_KIBANA_USERNAME=kibana_system
WANWU_KIBANA_PASSWORD=
WANWU_NGINX_HOST=nginx-wanwu
WANWU_MYSQL_IMAGE=mysql:8.0.37
WANWU_REDIS_IMAGE=redis:7.0.15
WANWU_MINIO_IMAGE=minio/minio:RELEASE.2024-08-26T15-33-07Z
WANWU_KAFKA_IMAGE=bitnami/kafka:3.9
WANWU_ELASTIC_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.12.2
WANWU_KIBANA_IMAGE=docker.elastic.co/kibana/kibana:8.12.2
WANWU_NGINX_IMAGE=nginx:1.27
WANWU_GO_IMAGE=golang:1.22.12-bookworm
WANWU_BACKEND_IMAGE=wanwulite/backend:v0.1.0-ecdcf63
WANWU_FRONTEND_IMAGE=wanwulite/frontend:v0.1.0-ecdcf63
WANWU_AGENTSCOPE_IMAGE=wanwulite/agentscope:20250626-f80eb15
WANWU_RAG_IMAGE=wanwulite/rag:v1.0.0-ece7ec30
WANWU_AGENT_IMAGE=wanwulite/agent:1.1-250625
ZHIYIN_USE_PAMI_LLM=0
ZHIYIN_USE_PAMI_KNOWLEDGE=0
ZHIYIN_USE_PAMI_AUTH=0
```

- [ ] **Step 5: Implement local secret generation**

Create `deploy/init_env.py`. It must refuse to overwrite an existing `.env`, copy `.env.example`, and fill every empty `*_PASSWORD` value with `secrets.token_urlsafe(24)`:

```python
from __future__ import annotations

import secrets
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent
EXAMPLE = DEPLOY_ROOT / ".env.example"
TARGET = DEPLOY_ROOT / ".env"


def build_environment(source: str) -> str:
    rendered: list[str] = []
    for line in source.splitlines():
        if line.endswith("_PASSWORD="):
            line = f"{line}{secrets.token_urlsafe(24)}"
        rendered.append(line)
    return "\n".join(rendered) + "\n"


def main() -> int:
    if TARGET.exists():
        raise FileExistsError(f"refusing to overwrite {TARGET}")
    TARGET.write_text(build_environment(EXAMPLE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"created {TARGET} with generated local secrets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Extend `test_deploy_assets.py` with:

```python
def test_init_env_generates_passwords_without_changing_public_values() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("init_env", DEPLOY / "init_env.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rendered = module.build_environment("PUBLIC=value\nDB_PASSWORD=\n")
    assert "PUBLIC=value" in rendered
    assert "DB_PASSWORD=\n" not in rendered
```

- [ ] **Step 6: Implement lifecycle scripts**

Create `deploy/up.ps1`:

```powershell
$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $DeployRoot
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw 'deploy/.env is missing; run python deploy/init_env.py first'
}
if (-not (docker network ls --format '{{.Name}}' | Select-String -SimpleMatch 'wanwu-net')) {
    docker network create wanwu-net | Out-Null
}
docker compose --project-directory $RepoRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose up -d --build
```

Create `deploy/down.ps1`:

```powershell
$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $DeployRoot
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
docker compose --project-directory $RepoRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose down
```

Create `deploy/verify.ps1`:

```powershell
$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $DeployRoot
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
docker compose --project-directory $RepoRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose config --quiet
$Wanwu = Invoke-RestMethod -Uri 'http://127.0.0.1:8081/user/api/v1/base/custom' -TimeoutSec 15
$Zhiyin = docker compose --project-directory $RepoRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose exec -T zhiyin-api python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz')))"
if (-not $Wanwu) { throw 'Wanwu business readiness failed' }
if (-not $Zhiyin) { throw 'zhiyin health check failed' }
Write-Output 'unified deployment baseline is ready'
```

- [ ] **Step 7: Run static tests and render the Compose model**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest tests/test_deploy_assets.py -v
Set-Location ../..
python deploy/init_env.py
docker compose --project-directory . --env-file deploy/.env -f platform/wanwu/docker-compose.yaml -f deploy/compose.yaml config --quiet
```

Expected: tests pass, `.env` is generated and ignored, and Compose configuration renders without interpolation or schema errors.

- [ ] **Step 8: Start and verify the unified stack**

Run from the repository root:

```powershell
pwsh deploy/up.ps1
pwsh deploy/verify.ps1
```

Expected: Wanwu's public base endpoint responds, the zhiyin container reports `/healthz`, and verification prints `unified deployment baseline is ready`.

- [ ] **Step 9: Stop without deleting data**

Run:

```powershell
pwsh deploy/down.ps1
```

Expected: containers stop and named volumes remain.

- [ ] **Step 10: Commit deployment assets**

```powershell
git add deploy/compose.yaml deploy/.env.example deploy/init_env.py deploy/up.ps1 deploy/down.ps1 deploy/verify.ps1 zhiyin-src/template/tests/test_deploy_assets.py
git commit -m "build: add unified wanwu and zhiyin deployment"
```

---

### Task 5: CI and Operator Documentation

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/README.md`
- Test: full repository verification commands.

**Interfaces:**
- Consumes: vendor tests, backend Dockerfile, deployment assets, and existing CI gates.
- Produces: CI enforcement and a documented local operator flow.

- [ ] **Step 1: Add CI verification for the new baseline**

In `.github/workflows/ci.yml`, add these steps to the existing `backend` job after the phase-one gate:

```yaml
      - name: Wanwu 源码快照与部署资产边界
        run: python -m pytest tests/test_wanwu_vendor.py tests/test_container_assets.py tests/test_deploy_assets.py -q

      - name: 构建职引后端镜像
        run: docker build --tag zhiyin/backend:ci .

      - name: 容器内里程碑门禁
        run: docker run --rm zhiyin/backend:ci python -m zhiyin_boot --check --phase=1
```

Add a repository-root job for Compose rendering because its paths are relative to `deploy/compose.yaml`:

```yaml
  deployment:
    name: 统一部署配置
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: 生成一次性本地环境
        run: python deploy/init_env.py
      - name: 校验 Compose 模型
        run: docker compose --project-directory . --env-file deploy/.env -f platform/wanwu/docker-compose.yaml -f deploy/compose.yaml config --quiet
```

- [ ] **Step 2: Document the operator workflow**

Add a “内置 pami/Wanwu 部署基线” section to `README.md` with these commands and an explicit phase statement:

```markdown
## 内置 pami/Wanwu 部署基线

Wanwu 源码位于 `platform/wanwu/`，职引后端与 Wanwu 通过 `wanwu-net` 内部网络运行。

```powershell
python deploy/init_env.py
pwsh deploy/up.ps1
pwsh deploy/verify.ps1
pwsh deploy/down.ps1
```

当前完成的是源码与统一部署基线。`ZHIYIN_USE_PAMI_*` 保持关闭；运行面和控制面
Adapter 将在后续阶段实现并通过真实接口测试后启用。
```

Add links to the approved spec and this plan under `docs/README.md` “架构” section.

- [ ] **Step 3: Run the complete verification suite**

Run:

```powershell
Set-Location zhiyin-src/template
python -m pytest -q
python -m ruff check . ../../scripts/import_wanwu.py
python scripts/export_openapi.py --check
python -m zhiyin_boot --check --phase=1
Set-Location zhiyin-web
npm ci --no-audit --no-fund
npm run typecheck
npm run check:api
Set-Location ../../..
docker compose --project-directory . --env-file deploy/.env -f platform/wanwu/docker-compose.yaml -f deploy/compose.yaml config --quiet
```

Expected: all commands exit zero. `npm run check:api` leaves no generated diff.

- [ ] **Step 4: Confirm repository cleanliness and boundary**

Run from the repository root:

```powershell
git status --short
git diff --check
git ls-files platform/wanwu/.env platform/wanwu/.env.bak deploy/.env
```

Expected: only Task 5 documentation and CI changes are uncommitted before the final commit; `git diff --check` prints nothing; the secret-file query prints nothing.

- [ ] **Step 5: Commit CI and documentation**

```powershell
git add .github/workflows/ci.yml README.md docs/README.md
git commit -m "docs: document embedded wanwu deployment baseline"
```

- [ ] **Step 6: Record final evidence**

Run:

```powershell
git log -5 --oneline --decorate
git status --short
```

Expected: five focused implementation commits are present after the design and plan commits, and the working tree is clean.
