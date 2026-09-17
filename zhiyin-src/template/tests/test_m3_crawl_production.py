from __future__ import annotations

import json

import pytest

from zhiyin_infrastructure.crawl import (
    CrawlPausedError,
    KnowledgeIngestionPipeline,
    KnowledgeSource,
    ProductionCrawlRunner,
    ReviewDecision,
)


def _source() -> KnowledgeSource:
    return KnowledgeSource(
        source_id="open-api",
        name="公开接口",
        source_url="https://example.test/api",
        namespace="occupation",
        acquisition="open_api",
        access_basis="公开授权接口",
        allowed=True,
        allowed_scope="公开职业字段",
        owner="数据负责人",
        refresh_interval="daily",
        removal_method="按 source_id 下架",
        retention="长期复核",
        status="enabled",
    )


@pytest.mark.asyncio
async def test_production_crawl_persists_stage_and_supports_incremental(tmp_path) -> None:
    indexed: list[str] = []
    pipeline = KnowledgeIngestionPipeline(
        tmp_path / "knowledge",
        on_index_updated=indexed.append,
        reviewer=lambda source, item: ReviewDecision(
            status="approved", reviewer="test", reason="固定测试数据"
        ),
    )
    runner = ProductionCrawlRunner(pipeline, tmp_path / "jobs")
    payload = {"items": [{"id": "dev", "name": "软件开发"}]}

    first = await runner.run(_source(), lambda source: payload, job_id="job-1")
    second = await runner.run(_source(), lambda source: payload, job_id="job-2")

    assert first.stored == 1
    assert second.unchanged == 1
    assert indexed == ["occupation"]
    state = json.loads((tmp_path / "jobs" / "job-2.json").read_text("utf-8"))
    assert state["status"] == "completed"
    assert state["stage"] == "done"


@pytest.mark.asyncio
async def test_production_crawl_pauses_on_shape_change_and_alerts(tmp_path) -> None:
    alerts: list[dict[str, object]] = []
    runner = ProductionCrawlRunner(
        KnowledgeIngestionPipeline(tmp_path / "knowledge"),
        tmp_path / "jobs",
        alert=alerts.append,
    )

    with pytest.raises(CrawlPausedError):
        await runner.run(_source(), lambda source: {"items": "unexpected"}, job_id="bad")

    state = json.loads((tmp_path / "jobs" / "bad.json").read_text("utf-8"))
    assert state["status"] == "paused"
    assert alerts[0]["type"] == "crawl_source_paused"
