"""向量同步的 metadata 透传测试（D7：让"状态/权限过滤"在向量通道真的成立）。

真实故障背景：检索计划给每条 query 带 `filters={"status": "enabled"}`，而
`PgVectorGateway` 用 `metadata @> filters` 过滤；向量行里原本**没有** `status`
字段，于是过滤恒不命中、向量通道恒返回 0 条——表现为"检索没有内容"，
而真正的原因是过滤字段没被写进向量 metadata。
"""

from __future__ import annotations

import pytest

from zhiyin_infrastructure.mysql.repositories import DatabaseContext
from zhiyin_infrastructure.persistence.embed_tasks import EmbedTaskStore
from zhiyin_infrastructure.workers.vector_sync import VectorSyncPlanner


@pytest.mark.asyncio
async def test_status_and_owner_are_carried_into_vector_metadata() -> None:
    """`status` / `user_id` / `org_id` 必须进向量 metadata，否则过滤会滤掉所有向量行。"""
    context = DatabaseContext("sqlite+aiosqlite:///:memory:", auto_create=True)
    store = EmbedTaskStore(context)
    planner = VectorSyncPlanner(store, vector=None, model="m")  # type: ignore[arg-type]

    await planner.schedule_incremental(
        "theory",
        [
            {
                "id": "doc-1",
                "title": "标题",
                "content": "正文",
                "source_id": "doc-1",
                "source_url": "https://example.org/x",
                "version": 2,
                "status": "enabled",
                "user_id": "",
                "org_id": "org-1",
            }
        ],
    )
    tasks = await store.claim(limit=5)
    assert len(tasks) == 1
    metadata = tasks[0].metadata
    assert metadata["status"] == "enabled"
    assert metadata["user_id"] == ""
    assert metadata["org_id"] == "org-1"
    assert metadata["source_id"] == "doc-1"
    assert metadata["version"] == 2
