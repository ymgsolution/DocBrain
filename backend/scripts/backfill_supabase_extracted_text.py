"""One-time backfill: upload every extracted-text .txt file (whose parent
document_version was already migrated to Supabase) to Supabase Storage,
verify the upload by content comparison, then delete the local .txt copy.

Companion to backfill_supabase_storage.py — that one migrates the original
document bytes; this one migrates their derived .txt siblings, closing the
one remaining gap where MetadataGenerationService/EmbeddingGenerationService
read extracted text via the worker's single configured storage adapter
(not per-row resolved, unlike document content reads — see PROJECT_STATUS.md
§9's documented reasoning for why that's an accepted, low-risk gap normally;
migrating these too removes it entirely for every document with real content).

document_extracted_text has no stored checksum column (unlike
document_versions), so verification here is a direct byte-for-byte content
comparison against the local file, not a checksum column match.

Safe to re-run: a .txt file already gone locally is skipped (already done).

Usage: uv run python -m scripts.backfill_supabase_extracted_text
"""

from pathlib import Path

from sqlalchemy import text as sql_text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.storage.supabase_adapter import SupabaseStorageAdapter


def main() -> None:
    settings = get_settings()
    supabase = SupabaseStorageAdapter()
    root = Path(settings.storage_root).resolve()

    db = SessionLocal()
    try:
        rows = db.execute(
            sql_text(
                """
                SELECT det.extracted_text_path, dv.storage_provider
                FROM document_extracted_text det
                JOIN document_versions dv ON dv.id = det.document_version_id
                WHERE det.extracted_text_path IS NOT NULL
                """
            )
        ).all()

        migrated = 0
        skipped_missing = 0
        skipped_not_supabase = 0
        failed = 0

        for extracted_text_path, storage_provider in rows:
            if storage_provider != "supabase":
                # Original content itself is still local — migrating its
                # .txt sibling ahead of the original would be inconsistent.
                skipped_not_supabase += 1
                continue

            full_path = root / extracted_text_path
            if not full_path.is_file():
                skipped_missing += 1
                continue

            local_content = full_path.read_bytes()
            try:
                supabase._client.upload_file(str(full_path), supabase._bucket, extracted_text_path)
                with supabase.open_for_read(extracted_text_path) as remote_stream:
                    remote_content = remote_stream.read()

                if remote_content != local_content:
                    print(f"CONTENT MISMATCH, not deleting local copy: {extracted_text_path}")
                    failed += 1
                    continue

                full_path.unlink()
                migrated += 1
                print(f"migrated + verified + deleted local copy: {extracted_text_path} ({len(local_content)} bytes)")
            except Exception as exc:
                print(f"FAILED: {extracted_text_path} — {exc}")
                failed += 1

        print(
            f"\nDone. migrated={migrated} skipped_missing_locally={skipped_missing} "
            f"skipped_original_not_yet_supabase={skipped_not_supabase} failed={failed}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
