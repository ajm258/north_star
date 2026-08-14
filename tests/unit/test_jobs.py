from __future__ import annotations

from datetime import UTC, datetime

from portfolio_intelligence.domain.enums import JobStatus
from portfolio_intelligence.services.jobs import FreshnessCheck, JobService


def test_jobs_are_idempotent_and_block_stale_valuation(session) -> None:
    service = JobService()
    as_of = datetime(2025, 1, 1, tzinfo=UTC)
    first = service.enqueue(
        session,
        job_type="valuation_report",
        scope_type="portfolio",
        scope_id="portfolio-1",
        logical_as_of=as_of,
    )
    same = service.enqueue(
        session,
        job_type="valuation_report",
        scope_type="portfolio",
        scope_id="portfolio-1",
        logical_as_of=as_of,
    )
    service.start(session, first.id)
    blocked = service.gate_valuation_freshness(
        session,
        first.id,
        [FreshnessCheck(source="fx", observed_at=None, is_stale=True, reason="No rate")],
    )

    assert first.id == same.id
    assert blocked.status == JobStatus.BLOCKED_STALE
    assert blocked.error == {"code": "STALE_REQUIRED_DATA", "sources": ["fx"]}
