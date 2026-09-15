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
BLOCKED_PARTS = frozenset({".git", ".cache", ".pytest_cache", "output", "__pycache__"})


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
