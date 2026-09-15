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
    cache = source / ".pytest_cache"
    cache.mkdir()
    (cache / "state").write_text("local test state", encoding="utf-8")
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
    assert not (destination / ".pytest_cache").exists()
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
