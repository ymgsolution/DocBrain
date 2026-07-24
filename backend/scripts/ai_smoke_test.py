"""Manual, real-API smoke test for the Gemini metadata-generation integration
— not part of the automated test suite (it makes real network calls and
costs real tokens). Run once after setting GEMINI_API_KEY, before trusting
the worker loop with live traffic: picks a few already-extracted real
documents, calls Gemini for real, and prints the result. Makes no DB writes.

Usage: uv run python -m scripts.ai_smoke_test [--limit N]
"""

import argparse
import sys

from sqlalchemy import select

from app.ai.gemini_provider import GeminiProvider
from app.ai.prompts.registry import get_prompt
from app.ai.schemas import MetadataSuggestion
from app.core.config import get_settings
from app.db.models import Document, DocumentExtractedText, DocumentVersion
from app.db.models.enums import ExtractionStatus
from app.db.session import SessionLocal
from app.storage.local_adapter import LocalFileSystemStorage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is not set in .env — nothing to smoke test.", file=sys.stderr)
        raise SystemExit(1)

    storage = LocalFileSystemStorage()
    provider = GeminiProvider(
        api_key=settings.gemini_api_key, model=settings.gemini_model, max_retries=settings.ai_max_retries
    )
    prompt = get_prompt("metadata_generation")

    db = SessionLocal()
    try:
        stmt = (
            select(DocumentExtractedText)
            .where(DocumentExtractedText.status == ExtractionStatus.SUCCEEDED, DocumentExtractedText.char_count > 0)
            .limit(args.limit)
        )
        rows = list(db.scalars(stmt))
        if not rows:
            print("No successfully-extracted documents found — start the worker and let extraction run first.")
            return

        for row in rows:
            version = db.get(DocumentVersion, row.document_version_id)
            assert version is not None
            document = db.get(Document, version.document_id)
            title = document.title if document is not None else version.original_filename

            assert row.extracted_text_path is not None
            with storage.open_for_read(row.extracted_text_path) as stream:
                text = stream.read().decode("utf-8", errors="replace")
            truncated = text[: settings.ai_max_extracted_text_chars]

            print(f"\n=== {title} ({version.original_filename}) ===")
            try:
                response = provider.generate_structured(
                    system_prompt=prompt.system,
                    user_prompt=prompt.render_user(title=title, extracted_text=truncated),
                    response_schema=MetadataSuggestion,
                    timeout_seconds=settings.ai_request_timeout_seconds,
                )
            except Exception as exc:  # noqa: BLE001 - a smoke test wants to see every failure, not just AIProviderError
                print(f"  FAILED: {exc}")
                continue

            suggestion = response.data
            assert isinstance(suggestion, MetadataSuggestion)
            print(f"  title:       {suggestion.title}")
            print(f"  summary:     {suggestion.summary}")
            print(f"  tags:        {suggestion.tags}")
            print(f"  usage:       {response.usage}")
            print(f"  latency_ms:  {response.latency_ms}  retries: {response.retry_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
