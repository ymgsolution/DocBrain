import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AiJob
from app.db.models.enums import AiJobStatus, AiJobType

MAX_ATTEMPTS = 5
_BACKOFF_BASE_SECONDS = 30
_BACKOFF_CAP_SECONDS = 3600


class AiJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enqueue(self, *, job_type: AiJobType, document_version_id: uuid.UUID) -> AiJob:
        """Caller is expected to insert this in the same transaction as the
        upload/version-create it's reacting to (mirrors how ActivityEvent
        rows are already written) — no separate commit here."""
        job = AiJob(job_type=job_type, document_version_id=document_version_id)
        self.db.add(job)
        return job

    def claim_batch(self, *, job_type: AiJobType, limit: int) -> list[AiJob]:
        """SELECT ... FOR UPDATE SKIP LOCKED — the same row-locking pattern
        already used for version-number allocation (versions/repository.py),
        applied here so multiple worker processes can poll concurrently
        without two of them claiming the same job."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(AiJob)
            .where(
                AiJob.job_type == job_type,
                AiJob.status == AiJobStatus.PENDING,
                AiJob.attempt_count < MAX_ATTEMPTS,
                (AiJob.next_retry_at.is_(None)) | (AiJob.next_retry_at <= now),
            )
            .order_by(AiJob.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(self.db.scalars(stmt))
        for job in jobs:
            job.status = AiJobStatus.PROCESSING
            job.started_at = now
            job.attempt_count += 1
        self.db.commit()
        return jobs

    def mark_succeeded(self, job: AiJob) -> None:
        job.status = AiJobStatus.SUCCEEDED
        job.completed_at = datetime.now(timezone.utc)
        job.last_error = None
        self.db.commit()

    def mark_failed(self, job: AiJob, *, error: str) -> None:
        job.last_error = error[:2000]
        if job.attempt_count >= MAX_ATTEMPTS:
            job.status = AiJobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.next_retry_at = None
        else:
            # Exponential backoff: 30s, 60s, 120s, 240s, capped at 1h.
            delay = min(_BACKOFF_BASE_SECONDS * (2 ** (job.attempt_count - 1)), _BACKOFF_CAP_SECONDS)
            job.status = AiJobStatus.PENDING
            job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        self.db.commit()
