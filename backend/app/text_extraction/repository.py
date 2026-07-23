import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentExtractedText


class DocumentExtractedTextRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_version_id(self, document_version_id: uuid.UUID) -> DocumentExtractedText | None:
        stmt = select(DocumentExtractedText).where(DocumentExtractedText.document_version_id == document_version_id)
        return self.db.scalar(stmt)

    def get_or_create(self, document_version_id: uuid.UUID) -> DocumentExtractedText:
        existing = self.get_by_version_id(document_version_id)
        if existing is not None:
            return existing
        row = DocumentExtractedText(document_version_id=document_version_id)
        self.db.add(row)
        self.db.flush()
        return row
