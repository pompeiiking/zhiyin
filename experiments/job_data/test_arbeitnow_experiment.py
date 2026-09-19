from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from arbeitnow_experiment import build_snapshot, normalize_payload


def _payload() -> dict:
    return {
        "data": [
            {
                "slug": "python-data-engineer-1",
                "company_name": "Example GmbH",
                "title": "Python Data Engineer",
                "description": (
                    "<p>Build <strong>data</strong> pipelines. "
                    "Contact recruiter@example.com or +49 30 12345678.</p>"
                ),
                "remote": True,
                "url": "https://www.arbeitnow.com/jobs/python-data-engineer-1",
                "tags": ["Python", "Python", "Data"],
                "job_types": ["full-time"],
                "location": " Berlin  ",
                "created_at": 1_700_000_000,
            },
            {
                "slug": "python-data-engineer-1",
                "title": "duplicate",
                "url": "https://www.arbeitnow.com/jobs/duplicate",
            },
            {"slug": "broken", "title": "Missing URL"},
        ]
    }


def test_normalizes_filters_deduplicates_and_hashes() -> None:
    fetched_at = datetime(2026, 9, 16, tzinfo=timezone.utc)
    jobs, rejected = normalize_payload(_payload(), keyword="python", limit=10, fetched_at=fetched_at)
    assert rejected == 0
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "arbeitnow-public-api:python-data-engineer-1"
    assert job.location == "Berlin"
    assert job.tags == ["Python", "Data"]
    assert job.description_summary == (
        "Build data pipelines. Contact [redacted-email] or [redacted-phone]."
    )
    assert job.fetched_at == "2026-09-16T00:00:00+00:00"
    assert len(job.content_hash) == 64


def test_invalid_matching_record_is_rejected() -> None:
    jobs, rejected = normalize_payload(_payload(), keyword="missing url", limit=10)
    assert jobs == []
    assert rejected == 1


def test_snapshot_never_persists_raw_response() -> None:
    jobs, rejected = normalize_payload(_payload(), limit=1)
    snapshot = build_snapshot(jobs, rejected=rejected, api_url="https://example.test/api")
    encoded = json.dumps(snapshot)
    assert snapshot["_meta"]["raw_response_persisted"] is False
    assert "<strong>" not in encoded
