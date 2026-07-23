from typing import BinaryIO

from pypdf import PdfReader

from app.text_extraction.port import ExtractionResult


class PdfExtractor:
    def extract(self, stream: BinaryIO) -> ExtractionResult:
        reader = PdfReader(stream)
        # An image-only/scanned PDF legitimately extracts to "" — not an
        # error, just nothing for the AI suggestion stage to work with.
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages).strip()
        return ExtractionResult(text=text, char_count=len(text))
