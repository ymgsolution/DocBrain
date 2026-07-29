import uuid
from typing import Protocol

from app.core.config import get_settings
from app.db.models import Document, DocumentVectorEmbedding
from app.db.models.enums import AiAnalysisStatus


class _EmbeddingLookup(Protocol):
    """The slice of DocumentVectorEmbeddingRepository this service actually
    calls — a Protocol (mirroring AIProvider/EmbeddingProvider elsewhere in
    app/ai/) rather than the concrete repository class, so tests can pass a
    small fake without needing a real DB session."""

    def get_by_version_id(self, document_version_id: uuid.UUID) -> DocumentVectorEmbedding | None: ...

    def find_similar(
        self,
        *,
        query_vector: list[float],
        exclude_document_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int,
    ) -> list[tuple[uuid.UUID, float]]: ...


class _DocumentLookup(Protocol):
    """The slice of DocumentRepository this service actually calls — same
    Protocol-over-concrete-class reasoning as _EmbeddingLookup above."""

    def get_active_by_id(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document | None: ...

    def list_by_ids(self, document_ids: list[uuid.UUID], organization_id: uuid.UUID) -> list[Document]: ...


class SimilarityService:
    """Similar Document Detection track — the reusable seam Duplicate
    Detection, Recommendations, and Semantic Search all sit on top of later:
    find_similar_documents takes a document, returns ranked (Document,
    score) pairs, no UI/endpoint concerns. Semantic Search will call the
    same DocumentVectorEmbeddingRepository.find_similar with a query-text
    embedding instead of a stored document's own vector; Duplicate Detection
    is the same call with a small limit and a higher min_similarity passed
    explicitly by the caller, overriding the org-wide default below. Lives
    in app/ai/ alongside metadata_service.py — same AI capability bucket,
    not a new top-level module."""

    def __init__(self, embeddings: _EmbeddingLookup, documents: _DocumentLookup) -> None:
        self.embeddings = embeddings
        self.documents = documents

    def find_similar_documents(
        self,
        document_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        limit: int = 5,
        min_similarity: float | None = None,
    ) -> list[tuple[Document, float]]:
        document = self.documents.get_active_by_id(document_id, organization_id)
        if document is None or document.current_version is None:
            return []

        embedding_row = self.embeddings.get_by_version_id(document.current_version.id)
        if (
            embedding_row is None
            or embedding_row.status != AiAnalysisStatus.SUCCEEDED
            or embedding_row.embedding is None
        ):
            # Not ready yet (still PENDING/PROCESSING) or never will be
            # (FAILED/SKIPPED) — same "null means not ready" convention as
            # ai_suggestion, not an error.
            return []

        threshold = min_similarity if min_similarity is not None else get_settings().similarity_min_score

        ranked = self.embeddings.find_similar(
            query_vector=embedding_row.embedding,
            exclude_document_id=document.id,
            organization_id=organization_id,
            limit=limit,
        )
        # A "top N by rank" match is meaningless if none of them are actually
        # close — e.g. two documents that only share generic boilerplate.
        # Below threshold, show nothing rather than a misleading weak match,
        # same "quiet, self-clearing" convention as the rest of this card.
        ranked = [(doc_id, score) for doc_id, score in ranked if score >= threshold]
        if not ranked:
            return []

        scores_by_id = dict(ranked)
        hydrated_by_id = {
            doc.id: doc
            for doc in self.documents.list_by_ids([doc_id for doc_id, _ in ranked], organization_id)
        }

        # Re-sort by the original ranked order — list_by_ids doesn't
        # guarantee it, and a document could in principle vanish between the
        # two queries (hard-deleted mid-request); skip it rather than error.
        return [
            (hydrated_by_id[doc_id], scores_by_id[doc_id]) for doc_id, _ in ranked if doc_id in hydrated_by_id
        ]
