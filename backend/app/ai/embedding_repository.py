import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentVectorEmbedding, DocumentVersion
from app.db.models.enums import AiAnalysisStatus, DocumentStatus


class DocumentVectorEmbeddingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_version_id(self, document_version_id: uuid.UUID) -> DocumentVectorEmbedding | None:
        stmt = select(DocumentVectorEmbedding).where(
            DocumentVectorEmbedding.document_version_id == document_version_id
        )
        return self.db.scalar(stmt)

    def get_or_create(self, document_version_id: uuid.UUID) -> DocumentVectorEmbedding:
        existing = self.get_by_version_id(document_version_id)
        if existing is not None:
            return existing
        row = DocumentVectorEmbedding(document_version_id=document_version_id)
        self.db.add(row)
        self.db.flush()
        return row

    def find_similar(
        self, *, query_vector: list[float], exclude_document_id: uuid.UUID, limit: int
    ) -> list[tuple[uuid.UUID, float]]:
        """Returns (document_id, cosine_similarity) pairs, most similar
        first, over every ACTIVE document's current-version SUCCEEDED
        embedding except the excluded document itself.

        Joins through document_versions/documents (not a bare
        embedding-to-embedding query) deliberately: "similar to an old,
        no-longer-current version" or "similar to a soft-deleted document"
        isn't a real result for any consumer (Similar Documents, Duplicate
        Detection, Semantic Search all want active, current-version matches
        only), so that filtering belongs in this one shared query rather
        than being re-implemented by every caller.

        Returns bare document_ids, not hydrated Document rows — this
        repository doesn't own how a Document should be eager-loaded for a
        response; SimilarityService hydrates via DocumentRepository."""
        distance = DocumentVectorEmbedding.embedding.cosine_distance(query_vector)
        stmt = (
            select(Document.id, distance.label("distance"))
            .join(DocumentVersion, DocumentVersion.id == Document.current_version_id)
            .join(DocumentVectorEmbedding, DocumentVectorEmbedding.document_version_id == DocumentVersion.id)
            .where(
                DocumentVectorEmbedding.status == AiAnalysisStatus.SUCCEEDED,
                Document.status == DocumentStatus.ACTIVE,
                Document.id != exclude_document_id,
            )
            .order_by(distance)
            .limit(limit)
        )
        return [(row.id, 1 - row.distance) for row in self.db.execute(stmt).all()]
