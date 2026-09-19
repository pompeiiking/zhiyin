"""把 `data/registry/*.json` 显式同步到数据库 `registry_resource`。

为什么需要这个脚本
------------------
动态资源 Repository 只在 `registry_resource` **整表为空**时按 JSON 播种。
一旦环境里已经有数据，后续对 `data/registry/*.json` 的修改（新增关键词、
调整阈值、改文案）都**不会**生效，也不会报错——这是最贵的一类漂移：
线上"改了 JSON 却没生效"，而门禁全绿。

因此把同步做成一次**显式、可复核**的发布动作，而不是隐式自动覆盖：

    python scripts/sync_registry.py            # 只报告差异（默认，不改库）
    python scripts/sync_registry.py --check     # 有差异就退出码 1，供门禁使用
    python scripts/sync_registry.py --apply     # 实际写入（幂等 upsert）

口径
----
- 唯一键是 `(kind, resource_key)`，键的算法与 Repository 的播种逻辑**共用同一份**实现，
  避免两处各拼一次键。
- 只新增与更新；**不删除**数据库里多出来的行，只把它们列出来提示人工确认——
  删配置要有人负责，不能让同步脚本顺手删掉。
- `--apply` 幂等：内容一致的记录不写、不改 `updated_at`。

环境变量：`ZHIYIN_DATABASE_URL`（必填）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select  # noqa: E402

from zhiyin_infrastructure.mysql import DatabaseContext  # noqa: E402
from zhiyin_infrastructure.mysql.repositories import (  # noqa: E402
    SqlAlchemyRegistryRepository,
)
from zhiyin_infrastructure.persistence.models import RegistryResourceRow  # noqa: E402


def desired_items(seed_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """按唯一键收集 JSON 里期望存在的资源。"""
    desired: dict[tuple[str, str], dict[str, Any]] = {}
    for kind, filename in SqlAlchemyRegistryRepository.FILES.items():
        path = seed_dir / filename
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("items", []) if isinstance(raw, dict) else raw
        for item in items:
            key = SqlAlchemyRegistryRepository._resource_key(kind, item)
            if not key:
                continue
            desired[(kind, key)] = item
    return desired


async def sync(
    *, seed_dir: Path, apply: bool, database_url: str | None = None
) -> int:
    if database_url is None:
        database_url = os.getenv("ZHIYIN_DATABASE_URL", "").strip()
    if not database_url:
        print("ZHIYIN_DATABASE_URL 未配置，无法同步动态资源")
        return 2

    desired = desired_items(seed_dir)
    context = DatabaseContext(database_url)
    await context.ensure_ready()
    added = updated = unchanged = 0
    db_only: list[str] = []
    try:
        async with context.sessions.begin() as session:
            rows = list((await session.scalars(select(RegistryResourceRow))).all())
            existing = {(row.kind, row.resource_key): row for row in rows}
            now = datetime.now(timezone.utc)
            for (kind, key), item in sorted(desired.items()):
                payload_status = str(item.get("status", "enabled"))
                payload_sort = int(item.get("sort_order", 0))
                payload_bundle = str(item.get("bundle", ""))
                row = existing.get((kind, key))
                if row is None:
                    added += 1
                    print(f"  + {kind}/{key}")
                    if apply:
                        session.add(
                            RegistryResourceRow(
                                kind=kind,
                                resource_key=key,
                                status=payload_status,
                                sort_order=payload_sort,
                                bundle=payload_bundle,
                                payload=item,
                                updated_at=now,
                            )
                        )
                    continue
                if row.payload != item:
                    updated += 1
                    print(f"  ~ {kind}/{key}")
                    if apply:
                        row.payload = item
                        row.status = payload_status
                        row.sort_order = payload_sort
                        row.bundle = payload_bundle
                        row.updated_at = now
                    continue
                unchanged += 1
            for kind, key in sorted(set(existing) - set(desired)):
                db_only.append(f"{kind}/{key}")
    finally:
        await context.close()

    mode = "已写入" if apply else "仅报告（未改库）"
    print(
        f"[registry-sync] {mode}：新增 {added}，更新 {updated}，一致 {unchanged}，"
        f"库中多出 {len(db_only)}"
    )
    for name in db_only:
        print(f"  ! 库中存在但 JSON 已无（需人工确认是否下架）：{name}")
    drift = added + updated + len(db_only)
    return 1 if drift else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="动态资源显式同步")
    parser.add_argument("--apply", action="store_true", help="实际写入数据库")
    parser.add_argument("--check", action="store_true", help="有差异时退出码 1")
    parser.add_argument(
        "--seed-dir",
        default=str(REPO_ROOT / "data" / "registry"),
        help="动态资源 JSON 目录",
    )
    args = parser.parse_args()
    if args.apply and args.check:
        print("--apply 与 --check 不能同时使用")
        return 2
    code = asyncio.run(sync(seed_dir=Path(args.seed_dir), apply=args.apply))
    if args.check:
        return code
    return 0 if code in (0, 1) else code


if __name__ == "__main__":
    raise SystemExit(main())
