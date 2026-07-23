import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.utils.slugify import slugify_filename


class LocalFileSystemStorage:
    def __init__(self, root: str | None = None) -> None:
        settings = get_settings()
        self.root = Path(root or settings.storage_root).resolve()
        self.tmp_dir = self.root / "tmp"
        self.documents_dir = self.root / "documents"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def save_temp(self, stream: BinaryIO) -> Path:
        temp_path = self.tmp_dir / f"{uuid.uuid4()}.part"
        with open(temp_path, "wb") as dest:
            shutil.copyfileobj(stream, dest)
        return temp_path

    def build_storage_path(self, document_id: uuid.UUID, version_number: int, filename: str) -> str:
        safe_name = slugify_filename(filename)
        return f"documents/{document_id}/v{version_number}__{safe_name}"

    def commit(self, temp_path: Path, storage_path: str) -> None:
        dest = self._resolve(storage_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_path), str(dest))

    def discard(self, temp_path: Path) -> None:
        temp_path.unlink(missing_ok=True)

    def copy(self, source_storage_path: str, dest_storage_path: str) -> None:
        src = self._resolve(source_storage_path)
        dest = self._resolve(dest_storage_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    def open_for_read(self, storage_path: str) -> BinaryIO:
        full_path = self._resolve(storage_path)
        if not full_path.is_file():
            raise FileNotFoundError(storage_path)
        return open(full_path, "rb")

    def delete(self, storage_path: str) -> None:
        full_path = self._resolve(storage_path)
        full_path.unlink(missing_ok=True)
        parent = full_path.parent
        if parent != self.documents_dir and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()

    def _resolve(self, storage_path: str) -> Path:
        full_path = (self.root / storage_path).resolve()
        try:
            full_path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Resolved path escapes the storage root.") from exc
        return full_path
