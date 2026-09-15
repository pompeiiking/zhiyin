"""Validate the checked-in Wanwu native route contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "deploy" / "wanwu-routes.json"
DEFAULT_NGINX = (
    REPO_ROOT
    / "platform"
    / "wanwu"
    / "configs"
    / "middleware"
    / "nginx"
    / "conf.d"
    / "aibase.conf"
)
LOCATION_PATTERN = re.compile(
    r"location\s+\^~\s+(?P<prefix>\S+)\s*\{(?P<body>.*?)^\s*\}",
    flags=re.DOTALL | re.MULTILINE,
)
PROXY_PASS_PATTERN = re.compile(r"proxy_pass\s+(?P<upstream>[^;\s]+)\s*;")


def parse_nginx_routes(text: str) -> dict[str, str]:
    """Return every prefix location that contains a proxy_pass target."""
    routes: dict[str, str] = {}
    for location in LOCATION_PATTERN.finditer(text):
        proxy_pass = PROXY_PASS_PATTERN.search(location.group("body"))
        if proxy_pass is not None:
            routes[location.group("prefix")] = proxy_pass.group("upstream")
    return routes


def validate_routes(manifest_path: Path, nginx_path: Path) -> list[str]:
    """Return deterministic diagnostics for missing or misrouted native routes."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    configured = parse_nginx_routes(nginx_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for route in manifest["routes"]:
        prefix = route["prefix"]
        expected = route["upstream"]
        actual = configured.get(prefix)
        if actual is None:
            errors.append(f"missing nginx location: {prefix}")
        elif actual != expected:
            errors.append(
                f"upstream mismatch for {prefix}: expected {expected}, got {actual}"
            )
    return errors


def validate_documentation(
    manifest_path: Path,
    document_paths: list[Path],
) -> list[str]:
    """Return routes whose declared documentation anchor is absent."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documentation = "\n".join(
        path.read_text(encoding="utf-8") for path in document_paths
    )
    return [
        f"undocumented route: {route['prefix']}"
        for route in manifest["routes"]
        if route["documentation_anchor"] not in documentation
    ]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--nginx", type=Path, default=DEFAULT_NGINX)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_routes(args.manifest, args.nginx)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Wanwu native route contract is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
