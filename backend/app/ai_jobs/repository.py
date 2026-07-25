import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
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

    def mark_failed(
        self, job: AiJob, *, error: str, retry_after_seconds: float | None = None, permanent: bool = False
    ) -> None:
        """retry_after_seconds/permanent let a handler's exception hint at
        how this specific failure should be scheduled — see
        AIProviderError's docstring (app/ai/port.py) for the full reasoning.
        Neither is AI-specific in principle: any job handler could raise an
        exception carrying these same attributes and get the same
        treatment, since the worker reads them via getattr(), not a type
        check tied to this queue.

        - permanent=True: skip the remaining retry budget entirely — this
          exact request can never succeed (e.g. a malformed request or a
          revoked API key), so waiting and trying again would just fail the
          same way every time.
        - retry_after_seconds set: this failure needs a longer, different
          wait than a normal transient error (e.g. quota exhaustion) — the
          quota-specific backoff schedule is used, floored by
          retry_after_seconds so a provider's own hint is never shortened,
          but never trusted blindly short either (still on the same
          minutes-not-seconds schedule, since a hint can be misleadingly
          short for what's actually a much longer quota window).
        - neither set: unchanged, existing behavior (the normal
          30s/60s/120s/240s transient-error backoff).
        """
        job.last_error = error[:2000]
        if permanent or job.attempt_count >= MAX_ATTEMPTS:
            job.status = AiJobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.next_retry_at = None
        else:
            if retry_after_seconds is not None:
                settings = get_settings()
                base_delay = settings.ai_quota_backoff_base_seconds * (2 ** (job.attempt_count - 1))
                delay = min(max(retry_after_seconds, base_delay), settings.ai_quota_backoff_cap_seconds)
            else:
                # Exponential backoff: 30s, 60s, 120s, 240s, capped at 1h.
                delay = min(_BACKOFF_BASE_SECONDS * (2 ** (job.attempt_count - 1)), _BACKOFF_CAP_SECONDS)
            job.status = AiJobStatus.PENDING
            job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        self.db.commit()
