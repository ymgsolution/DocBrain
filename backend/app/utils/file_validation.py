import magic

from app.core.config import get_settings
from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError

# Maps an allowed extension to the sniffed MIME types considered a legitimate
# match. OOXML formats (docx/xlsx/pptx) are zip containers, and not every
# libmagic build resolves them past "application/zip" — both are accepted.
EXTENSION_MIME_HINTS: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "doc": {"application/msword"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    "xls": {"application/vnd.ms-excel"},
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    "ppt": {"application/vnd.ms-powerpoint"},
    "pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    },
    "txt": {"text/plain"},
    "md": {"text/plain", "text/markdown"},
    "csv": {"text/plain", "text/csv"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
}


def allowed_extensions() -> set[str]:
    settings = get_settings()
    return {e.strip().lower() for e in settings.allowed_extensions.split(",") if e.strip()}


def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_extension(filename: str) -> str:
    ext = get_extension(filename)
    allowed = allowed_extensions()
    if ext not in allowed:
        raise UnsupportedMediaTypeError(
            f"That file type isn't supported. Allowed types: {', '.join(sorted(allowed))}.",
            fields=[{"field": "file", "message": "Unsupported file type."}],
        )
    return ext


def validate_size(size_bytes: int) -> None:
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the {settings.max_upload_size_mb} MB limit.",
            fields=[{"field": "file", "message": "File too large."}],
        )


def sniff_mime_type(sample: bytes) -> str:
    return magic.from_buffer(sample, mime=True)


def validate_content_matches_extension(ext: str, mime_type: str) -> None:
    allowed_mimes = EXTENSION_MIME_HINTS.get(ext)
    if allowed_mimes and mime_type not in allowed_mimes:
        raise UnsupportedMediaTypeError(
            "This file's content doesn't match its extension.",
            fields=[{"field": "file", "message": f"Expected {ext} content, detected {mime_type}."}],
        )
