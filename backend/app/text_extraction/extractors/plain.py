from typing import BinaryIO

from app.text_extraction.port import ExtractionResult


class PlainTextExtractor:
    """txt/md/csv — already text, no parsing needed. errors="replace" rather
    than raising on a stray non-UTF-8 byte; a best-effort extraction beats no
    extraction for a feature whose output is advisory, not authoritative."""

    def extract(self, stream: BinaryIO) -> ExtractionResult:
        text = stream.read().decode("utf-8", errors="replace")
        return ExtractionResult(text=text, char_count=len(text))
