"""动态资源显式同步（`scripts/sync_registry.py`）的回归测试。

锁住三件事：
1. 唯一键来源与 Repository 播种逻辑共用一份实现，不各拼一次；
2. 同步是**幂等**的：跑第二遍不应再产生差异；
3. 库中多出来的行只报告、不删除（删配置要有人负责）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = TEMPLATE_ROOT / "data" / "registry"
if str(TEMPLATE_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT))

from scripts.sync_registry import desired_items, sync  # noqa: E402
from zhiyin_infrastructure.mysql import DatabaseContext  # noqa: E402
from zhiyin_infrastructure.mysql.repositories import (  # noqa: E402
    SqlAlchemyRegistryRepository,
)
from zhiyin_infrastructure.persistence.models import RegistryResourceRow  # noqa: E402
from sqlalchemy import select  # noqa: E402


def test_desired_items_covers_every_declared_kind() -> None:
    desired = desired_items(DATA_DIR)
    assert desired, "动态资源目录读不到任何条目"
    kinds = {kind for kind, _ in desired}
    # 声明在 FILES 里的种类只要文件存在就必须有条目，避免"文件在、没人读"
    for kind, filename in SqlAlchemyRegistryRepository.FILES.items():
        if (DATA_DIR / filename).is_file():
            assert kind in kinds, f"{filename} 有文件但没有任何条目进入同步范围"


def test_desired_items_keys_are_unique_and_non_empty() -> None:
    desired = desired_items(DATA_DIR)
    for (kind, key) in desired:
        assert key.strip(), f"{kind} 存在空唯一键"
    # dict 的键天然去重，这里确认没有任何条目因空键被静默跳过
    raw_total = 0
    for filename in SqlAlchemyRegistryRepository.FILES.values():
        path = DATA_DIR / filename
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw_total += len(raw.get("items", []) if isinstance(raw, dict) else raw)
    assert len(desired) == raw_total, "有条目因缺唯一键被跳过，需补 id/code/key"


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_reports_no_drift(tmp_path) -> None:
    db_path = tmp_path / "registry.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    context = DatabaseContext(url, auto_create=True)
    await context.ensure_ready()
    await context.close()

    # 首次同步：全部新增
    assert await sync(seed_dir=DATA_DIR, apply=True, database_url=url) == 1
    # 再同步：应当零差异
    assert await sync(seed_dir=DATA_DIR, apply=True, database_url=url) == 0

    context = DatabaseContext(url)
    await context.ensure_ready()
    async with context.sessions() as session:
        rows = list((await session.scalars(select(RegistryResourceRow))).all())
    await context.close()
    assert len(rows) == len(desired_items(DATA_DIR))


@pytest.mark.asyncio
async def test_db_only_rows_are_reported_not_deleted(tmp_path) -> None:
    db_path = tmp_path / "registry_extra.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    context = DatabaseContext(url, auto_create=True)
    await context.ensure_ready()
    await context.close()
    assert await sync(seed_dir=DATA_DIR, apply=True, database_url=url) == 1

    # 人为插入一条 JSON 里没有的记录
    context = DatabaseContext(url)
    await context.ensure_ready()
    from datetime import datetime, timezone

    async with context.sessions.begin() as session:
        session.add(
            RegistryResourceRow(
                kind="faqs",
                resource_key="legacy_question",
                status="enabled",
                sort_order=0,
                bundle="",
                payload={"code": "legacy_question"},
                updated_at=datetime.now(timezone.utc),
            )
        )
    await context.close()

    # 有库中多出的行 → 退出码 1，但该行必须仍在
    assert await sync(seed_dir=DATA_DIR, apply=True, database_url=url) == 1
    context = DatabaseContext(url)
    await context.ensure_ready()
    async with context.sessions() as session:
        row = await session.get(RegistryResourceRow, ("faqs", "legacy_question"))
    await context.close()
    assert row is not None, "同步脚本不得删除人工配置"
