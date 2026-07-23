from typing import BinaryIO

import openpyxl

from app.text_extraction.port import ExtractionResult


class XlsxExtractor:
    def extract(self, stream: BinaryIO) -> ExtractionResult:
        # read_only streams rows instead of loading the whole sheet into
        # memory; data_only resolves formula cells to their last-computed
        # value rather than the formula source text.
        workbook = openpyxl.load_workbook(stream, read_only=True, data_only=True)
        try:
            parts: list[str] = []
            for sheet in workbook.worksheets:
                parts.append(f"# {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(value) for value in row if value is not None]
                    if cells:
                        parts.append(" | ".join(cells))
            text = "\n".join(parts)
            return ExtractionResult(text=text, char_count=len(text))
        finally:
            workbook.close()
