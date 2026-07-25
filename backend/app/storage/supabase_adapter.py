import io
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.utils.slugify import slugify_filename


class SupabaseStorageAdapter:
    """StoragePort against Supabase Storage's S3-compatible API (via boto3,
    not the Supabase-specific SDK) — the same client works unchanged against
    real AWS S3 or MinIO later, just a different endpoint/credentials.

    save_temp/commit still buffer through a local temp file first, same as
    LocalFileSystemStorage: the storage_path isn't known until after
    document.id is allocated (a DB flush), and buffering locally is what
    lets checksum/size be computed before that path exists. commit() then
    uploads the buffered bytes; it doesn't skip the local step.
    """

    provider_name = "supabase"

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.supabase_storage_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.supabase_storage_endpoint,
            region_name=settings.supabase_storage_region,
            aws_access_key_id=settings.supabase_storage_access_key_id,
            aws_secret_access_key=settings.supabase_storage_secret_access_key,
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )
        # Local scratch space for the save_temp/commit buffering above —
        # never permanent storage, just where bytes sit mid-upload.
        self.tmp_dir = Path(settings.storage_root).resolve() / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def save_temp(self, stream: BinaryIO) -> Path:
        temp_path = self.tmp_dir / f"{uuid.uuid4()}.part"
        with open(temp_path, "wb") as dest:
            shutil.copyfileobj(stream, dest)
        return temp_path

    def build_storage_path(self, document_id: uuid.UUID, version_number: int, filename: str) -> str:
        safe_name = slugify_filename(filename)
        return f"documents/{document_id}/v{version_number}__{safe_name}"

    def commit(self, temp_path: Path, storage_path: str) -> None:
        self._client.upload_file(str(temp_path), self._bucket, storage_path)
        temp_path.unlink(missing_ok=True)

    def discard(self, temp_path: Path) -> None:
        temp_path.unlink(missing_ok=True)

    def copy(self, source_storage_path: str, dest_storage_path: str) -> None:
        self._client.copy_object(
            Bucket=self._bucket,
            CopySource={"Bucket": self._bucket, "Key": source_storage_path},
            Key=dest_storage_path,
        )

    def open_for_read(self, storage_path: str) -> BinaryIO:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=storage_path)
        except ClientError as exc:
            # Checked via HTTP status, not exc.response["Error"]["Code"]:
            # Supabase's S3-compatible error body puts Code/Message at the
            # top level of the response instead of nested under "Error" the
            # way AWS does, so botocore's XML-shaped error parser leaves
            # "Error").get("Code") empty here — the status code is the one
            # field guaranteed to parse correctly regardless of body shape.
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 404:
                raise FileNotFoundError(storage_path) from exc
            raise
        # Buffered into BytesIO, not returned as the raw StreamingBody:
        # confirmed live that pypdf.PdfReader needs a genuinely seekable
        # stream (PDFs are parsed by seeking to the trailer/xref table at
        # the end first — true of every PDF/DOCX/XLSX/PPTX parser, not a
        # pypdf quirk) and botocore's StreamingBody is a forward-only HTTP
        # response that raises io.UnsupportedOperation("seek") the moment
        # anything tries. Downloads never noticed (StreamingResponse only
        # ever .read()s sequentially), but this silently broke text
        # extraction — and therefore every AI feature chained after it —
        # for every document uploaded since the move to Supabase. Bounded
        # by settings.max_upload_size_mb (25 MB today), so buffering the
        # whole object is a safe, simple fix at this app's scale — matches
        # what LocalFileSystemStorage.open_for_read already provides (a
        # real, fully-seekable file handle), not a new tradeoff.
        return io.BytesIO(response["Body"].read())

    def delete(self, storage_path: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=storage_path)
