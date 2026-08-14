from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_intelligence.domain.enums import JobStatus
from portfolio_intelligence.domain.models import JobRun


@dataclass(frozen=True)
class FreshnessCheck:
    source: str
    observed_at: datetime | None
    is_stale: bool
    reason: str | None = None


class JobService:
    """Persist idempotent job state and block valuation work when required data is stale."""

    def enqueue(
        self,
        session: Session,
        *,
        job_type: str,
        scope_type: str,
        scope_id: str,
        logical_as_of: datetime,
    ) -> JobRun:
        idempotency_key = f"{job_type}:{scope_type}:{scope_id}:{logical_as_of.isoformat()}"
        existing = session.scalar(select(JobRun).where(JobRun.idempotency_key == idempotency_key))
        if existing:
            return existing
        job = JobRun(
            job_type=job_type,
            scope_type=scope_type,
            scope_id=scope_id,
            logical_as_of=logical_as_of,
            idempotency_key=idempotency_key,
        )
        session.add(job)
        session.commit()
        return job

    def start(self, session: Session, job_id: str) -> JobRun:
        job = session.get(JobRun, job_id)
        if job is None:
            raise ValueError("Job not found.")
        if job.status != JobStatus.QUEUED:
            raise ValueError("Only queued jobs can be started.")
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.attempt_count += 1
        session.commit()
        return job

    def gate_valuation_freshness(
        self, session: Session, job_id: str, checks: list[FreshnessCheck]
    ) -> JobRun:
        job = session.get(JobRun, job_id)
        if job is None:
            raise ValueError("Job not found.")
        job.freshness = {"checks": [asdict(check) for check in checks]}
        stale = [check for check in checks if check.is_stale]
        if stale:
            job.status = JobStatus.BLOCKED_STALE
            job.completed_at = datetime.now(UTC)
            job.error = {"code": "STALE_REQUIRED_DATA", "sources": [check.source for check in stale]}
        session.commit()
        return job


    def succeed(self, session: Session, job_id: str) -> JobRun:
        job = session.get(JobRun, job_id)
        if job is None:
            raise ValueError("Job not found.")
        if job.status != JobStatus.RUNNING:
            raise ValueError("Only running jobs can succeed.")
        job.status = JobStatus.SUCCEEDED
        job.completed_at = datetime.now(UTC)
        session.commit()
        return job
