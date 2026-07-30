import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AiDocumentAnalysis


class AiDocumentAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_version_id(self, document_version_id: uuid.UUID) -> AiDocumentAnalysis | None:
        stmt = select(AiDocumentAnalysis).where(AiDocumentAnalysis.document_version_id == document_version_id)
        return self.db.scalar(stmt)

    def mark_reviewed(self, document_version_id: uuid.UUID, *, accepted_by: uuid.UUID) -> None:
        """Records that a user has finished acting on this version's AI
        suggestion (accepted or dismissed its title/tags) — the `accepted`/
        `accepted_by`/`accepted_at` columns existed since this table was
        first built for exactly this, unused until now. A no-op if the
        analysis row doesn't exist or hasn't succeeded — nothing to mark."""
        analysis = self.get_by_version_id(document_version_id)
        if analysis is None:
            return
        analysis.accepted = True
        analysis.accepted_by = accepted_by
        analysis.accepted_at = datetime.now(timezone.utc)
        self.db.commit()

    def get_or_create(self, document_version_id: uuid.UUID, organization_id: uuid.UUID) -> AiDocumentAnalysis:
        existing = self.get_by_version_id(document_version_id)
        if existing is not None:
            return existing
        row = AiDocumentAnalysis(document_version_id=document_version_id, organization_id=organization_id)
        self.db.add(row)
        self.db.flush()
        return row
