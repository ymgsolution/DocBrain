import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Document, DocumentVersion


class VersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_document(self, document_id: uuid.UUID) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .options(selectinload(DocumentVersion.uploader))
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(self.db.scalars(stmt))

    def get(self, document_id: uuid.UUID, version_number: int) -> DocumentVersion | None:
        stmt = (
            select(DocumentVersion)
            .options(selectinload(DocumentVersion.uploader))
            .where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == version_number,
            )
        )
        return self.db.scalar(stmt)

    def get_document_for_update(self, document_id: uuid.UUID) -> Document | None:
        """Row-locked fetch — prevents two concurrent uploads against the same
        document from allocating the same next version_number (§12.3, §14.1)."""
        stmt = select(Document).where(Document.id == document_id).with_for_update()
        return self.db.scalar(stmt)

    def next_version_number(self, document_id: uuid.UUID) -> int:
        stmt = (
            select(DocumentVersion.version_number)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        current_max = self.db.scalar(stmt)
        return (current_max or 0) + 1

    def add(self, version: DocumentVersion) -> None:
        self.db.add(version)
