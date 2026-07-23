from dataclasses import dataclass
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    char_count: int


class TextExtractor(Protocol):
    """One format, one extractor, no DB or storage knowledge — a pure
    bytes-in/text-out function, deliberately decoupled from the DB-facing
    ExtractionMethod enum so it stays trivially unit-testable. The caller
    (the extraction service, added alongside the worker) already knows which
    extractor it dispatched to and tags the DB row accordingly."""

    def extract(self, stream: BinaryIO) -> ExtractionResult: ...
