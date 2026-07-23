"""The AI worker's runnable entrypoint: `uv run python -m app.ai_jobs.main`.

Its own process — never imported by app/main.py or run inside a FastAPI
request. Shares the same Postgres connection config as the API (via
app/db/session.py's SessionLocal) but not the request path, so a slow or
failing extraction never affects API latency.
"""

from app.ai_jobs.worker import run_forever
from app.core.logging import configure_logging
from app.db.models.enums import AiJobType
from app.storage.local_adapter import LocalFileSystemStorage
from app.text_extraction.service import TextExtractionService

if __name__ == "__main__":
    configure_logging()
    extraction_service = TextExtractionService(LocalFileSystemStorage())
    run_forever(handlers={AiJobType.EXTRACT: extraction_service.process_job})
