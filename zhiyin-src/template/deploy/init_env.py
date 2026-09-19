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
