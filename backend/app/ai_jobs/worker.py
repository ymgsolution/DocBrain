import logging
import time
from collections.abc import Callable
from typing import TypeAlias

from sqlalchemy.orm import Session

from app.ai_jobs.repository import AiJobRepository
from app.db.models import AiJob
from app.db.models.enums import AiJobType
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

JobHandler: TypeAlias = Callable[[Session, AiJob], None]
"""A handler processes one job to completion or raises — the worker itself
owns marking success/failure via AiJobRepository; handlers never touch
job.status directly. (Step 5 registers the first real handler, for
AiJobType.EXTRACT; this loop has nothing to dispatch to until then.)"""


def run_once(db: Session, *, handlers: dict[AiJobType, JobHandler], batch_size: int = 5) -> int:
    """Claims and processes up to `batch_size` jobs per registered job_type.
    Returns the number of jobs processed (success + failure combined), so
    callers can poll less often when the queue is empty."""
    repository = AiJobRepository(db)
    processed = 0
    for job_type, handler in handlers.items():
        jobs = repository.claim_batch(job_type=job_type, limit=batch_size)
        for job in jobs:
            try:
                handler(db, job)
                repository.mark_succeeded(job)
            except Exception as exc:
                logger.exception(
                    "ai_job %s failed (job_type=%s, attempt=%s)", job.id, job_type.value, job.attempt_count
                )
                db.rollback()
                repository.mark_failed(job, error=str(exc))
            processed += 1
    return processed


def run_forever(
    *,
    handlers: dict[AiJobType, JobHandler],
    poll_interval_seconds: float = 15,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """The long-running worker entrypoint — its own process, sharing the same
    Postgres connection config as the API but never the request path.
    Deliberately not wired into main.py/app startup: it's `python -m
    app.ai_jobs.worker` (or equivalent) once Step 5 gives it a real handler
    to register. Backs off to `poll_interval_seconds` only when a full sweep
    finds nothing to do, so a busy queue drains without waiting out the gap."""
    logger.info("ai worker starting: poll_interval=%ss job_types=%s", poll_interval_seconds, list(handlers))
    while True:
        db = session_factory()
        try:
            processed = run_once(db, handlers=handlers)
        finally:
            db.close()
        if processed == 0:
            time.sleep(poll_interval_seconds)
