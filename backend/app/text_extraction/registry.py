from app.db.models.enums import ExtractionMethod
from app.text_extraction.extractors.docx import DocxExtractor
from app.text_extraction.extractors.pdf import PdfExtractor
from app.text_extraction.extractors.plain import PlainTextExtractor
from app.text_extraction.extractors.pptx import PptxExtractor
from app.text_extraction.extractors.xlsx import XlsxExtractor
from app.text_extraction.port import TextExtractor

# doc/ppt/xls (legacy binary Office formats) have no reliable pure-Python
# parser and are deliberately absent — those extensions resolve to
# ExtractionStatus.UNSUPPORTED rather than a bad-faith attempt.
_EXTENSION_EXTRACTORS: dict[str, tuple[TextExtractor, ExtractionMethod]] = {
    "pdf": (PdfExtractor(), ExtractionMethod.PDF),
    "docx": (DocxExtractor(), ExtractionMethod.DOCX),
    "xlsx": (XlsxExtractor(), ExtractionMethod.XLSX),
    "pptx": (PptxExtractor(), ExtractionMethod.PPTX),
    "txt": (PlainTextExtractor(), ExtractionMethod.PLAIN),
    "md": (PlainTextExtractor(), ExtractionMethod.PLAIN),
    "csv": (PlainTextExtractor(), ExtractionMethod.PLAIN),
}


def get_extractor(extension: str) -> tuple[TextExtractor, ExtractionMethod] | None:
    return _EXTENSION_EXTRACTORS.get(extension.lower())
