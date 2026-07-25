"""One-time backfill: upload every local-stored document_versions row whose
file actually exists on disk to Supabase Storage, verify the upload by
checksum, and only then flip that row's storage_provider to "supabase".

Rows with no local file (a separate, pre-existing gap unrelated to this
migration) and rows already stamped "supabase" are skipped. Local files are
left untouched — this only adds a copy in Supabase and updates the DB, it
never deletes anything.

Safe to re-run: anything already migrated (storage_provider == "supabase")
is skipped, and a row is only flipped after its checksum is verified against
what's now in the bucket.

Usage: uv run python -m scripts.backfill_supabase_storage
"""

from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import DocumentVersion
from app.db.session import SessionLocal
from app.storage.checksum import sha256_of_stream
from app.storage.supabase_adapter import SupabaseStorageAdapter


def main() -> None:
    settings = get_settings()
    supabase = SupabaseStorageAdapter()

    db = SessionLocal()
    try:
        versions = list(db.scalars(select(DocumentVersion).where(DocumentVersion.storage_provider == "local")))

        migrated = 0
        skipped_missing = 0
        failed = 0

        for version in versions:
            full_path = Path(settings.storage_root).resolve() / version.storage_path
            if not full_path.is_file():
                skipped_missing += 1
                continue

            try:
                supabase._client.upload_file(str(full_path), supabase._bucket, version.storage_path)

                # Verify by checksum, not just "the upload call didn't raise"
                # — read the object back from Supabase and hash it, compare
                # against the version's own stored checksum_sha256 (computed
                # at original upload time). Only flip the row if it matches.
                with supabase.open_for_read(version.storage_path) as remote_stream:
                    remote_checksum = sha256_of_stream(remote_stream)

                if remote_checksum != version.checksum_sha256:
                    print(f"CHECKSUM MISMATCH, not flipping: {version.storage_path}")
                    failed += 1
                    continue

                version.storage_provider = "supabase"
                db.commit()
                migrated += 1
                print(f"migrated: {version.storage_path} ({version.size_bytes} bytes)")
            except Exception as exc:
                db.rollback()
                print(f"FAILED: {version.storage_path} — {exc}")
                failed += 1

        print(
            f"\nDone. migrated={migrated} skipped_no_local_file={skipped_missing} "
            f"failed={failed} (local files left untouched on disk)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
