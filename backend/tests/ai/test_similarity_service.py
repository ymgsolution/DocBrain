"""SimilarityService's orchestration logic (not-ready short-circuits,
ranking, hydration/exclusion) tested against small fake repositories — no
DB, no mocking library. Document/DocumentVersion/DocumentVectorEmbedding are
real ORM model instances used as plain Python objects (never persisted),
same "real fixture, no mocking library" style as test_gemini_provider.py's
fake SDK client. The actual pgvector ANN query (find_similar's SQL) is
exercised live against the real database instead, not here — see the manual
verification in this session, not a unit test."""

import uuid

import pytest

from app.ai.similarity_service import SimilarityService
from app.db.models import Document, DocumentVectorEmbedding, DocumentVersion
from app.db.models.enums import AiAnalysisStatus, DocumentStatus

ORG_ID = uuid.uuid4()


def _make_document(*, title: str, with_version: bool = True) -> Document:
    doc_id = uuid.uuid4()
    version = None
    if with_version:
        version = DocumentVersion(
            id=uuid.uuid4(),
            document_id=doc_id,
            version_number=1,
            storage_path="x",
            original_filename="x.txt",
            mime_type="text/plain",
            size_bytes=10,
            checksum_sha256="a" * 64,
        )
    return Document(
        id=doc_id,
        title=title,
        status=DocumentStatus.ACTIVE,
        current_version_id=version.id if version else None,
        current_version=version,
    )


class _FakeEmbeddingRepository:
    def __init__(self, *, embedding_by_version_id: dict | None = None, similar_results: list | None = None) -> None:
        self._embedding_by_version_id = embedding_by_version_id or {}
        self._similar_results = similar_results or []
        self.find_similar_calls: list[dict] = []

    def get_by_version_id(self, document_version_id: uuid.UUID) -> DocumentVectorEmbedding | None:
        return self._embedding_by_version_id.get(document_version_id)

    def find_similar(
        self,
        *,
        query_vector: list[float],
        exclude_document_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int,
    ) -> list[tuple[uuid.UUID, float]]:
        self.find_similar_calls.append(
            {
                "query_vector": query_vector,
                "exclude_document_id": exclude_document_id,
                "organization_id": organization_id,
                "limit": limit,
            }
        )
        return self._similar_results[:limit]


class _FakeDocumentRepository:
    def __init__(self, *, document_by_id: dict | None = None) -> None:
        self._document_by_id = document_by_id or {}

    def get_active_by_id(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document | None:
        return self._document_by_id.get(document_id)

    def list_by_ids(self, document_ids: list[uuid.UUID], organization_id: uuid.UUID) -> list[Document]:
        return [self._document_by_id[i] for i in document_ids if i in self._document_by_id]


def test_returns_empty_when_document_not_found() -> None:
    service = SimilarityService(_FakeEmbeddingRepository(), _FakeDocumentRepository())
    assert service.find_similar_documents(uuid.uuid4(), organization_id=ORG_ID) == []


def test_returns_empty_when_document_has_no_current_version() -> None:
    doc = _make_document(title="No version", with_version=False)
    documents = _FakeDocumentRepository(document_by_id={doc.id: doc})
    service = SimilarityService(_FakeEmbeddingRepository(), documents)
    assert service.find_similar_documents(doc.id, organization_id=ORG_ID) == []


def test_returns_empty_when_own_embedding_row_missing() -> None:
    doc = _make_document(title="Query doc")
    documents = _FakeDocumentRepository(document_by_id={doc.id: doc})
    service = SimilarityService(_FakeEmbeddingRepository(), documents)
    assert service.find_similar_documents(doc.id, organization_id=ORG_ID) == []


@pytest.mark.parametrize("status", [AiAnalysisStatus.PENDING, AiAnalysisStatus.FAILED, AiAnalysisStatus.SKIPPED])
def test_returns_empty_when_own_embedding_not_succeeded(status: AiAnalysisStatus) -> None:
    doc = _make_document(title="Query doc")
    assert doc.current_version is not None
    embedding_row = DocumentVectorEmbedding(document_version_id=doc.current_version.id, status=status, embedding=None)
    embeddings = _FakeEmbeddingRepository(embedding_by_version_id={doc.current_version.id: embedding_row})
    documents = _FakeDocumentRepository(document_by_id={doc.id: doc})
    service = SimilarityService(embeddings, documents)
    assert service.find_similar_documents(doc.id, organization_id=ORG_ID) == []


def test_returns_ranked_hydrated_results_in_order() -> None:
    query_doc = _make_document(title="Query doc")
    match_a = _make_document(title="Most similar")
    match_b = _make_document(title="Less similar")
    assert query_doc.current_version is not None

    query_vector = [0.1, 0.2, 0.3]
    embedding_row = DocumentVectorEmbedding(
        document_version_id=query_doc.current_version.id, status=AiAnalysisStatus.SUCCEEDED, embedding=query_vector
    )
    embeddings = _FakeEmbeddingRepository(
        embedding_by_version_id={query_doc.current_version.id: embedding_row},
        similar_results=[(match_a.id, 0.94), (match_b.id, 0.68)],
    )
    documents = _FakeDocumentRepository(
        document_by_id={query_doc.id: query_doc, match_a.id: match_a, match_b.id: match_b}
    )
    service = SimilarityService(embeddings, documents)

    results = service.find_similar_documents(query_doc.id, organization_id=ORG_ID, limit=5, min_similarity=0.0)

    assert [doc.title for doc, _ in results] == ["Most similar", "Less similar"]
    assert [score for _, score in results] == [0.94, 0.68]
    assert embeddings.find_similar_calls == [
        {
            "query_vector": query_vector,
            "exclude_document_id": query_doc.id,
            "organization_id": ORG_ID,
            "limit": 5,
        }
    ]


def test_skips_a_ranked_id_that_no_longer_hydrates() -> None:
    """A document could be hard-deleted between the ANN query and the
    hydration query — SimilarityService should skip it, not error."""
    query_doc = _make_document(title="Query doc")
    match = _make_document(title="Still here")
    vanished_id = uuid.uuid4()
    assert query_doc.current_version is not None

    embedding_row = DocumentVectorEmbedding(
        document_version_id=query_doc.current_version.id, status=AiAnalysisStatus.SUCCEEDED, embedding=[0.1]
    )
    embeddings = _FakeEmbeddingRepository(
        embedding_by_version_id={query_doc.current_version.id: embedding_row},
        similar_results=[(vanished_id, 0.99), (match.id, 0.5)],
    )
    documents = _FakeDocumentRepository(document_by_id={query_doc.id: query_doc, match.id: match})
    service = SimilarityService(embeddings, documents)

    results = service.find_similar_documents(query_doc.id, organization_id=ORG_ID, min_similarity=0.0)

    assert [doc.title for doc, _ in results] == ["Still here"]


def test_filters_out_matches_below_min_similarity() -> None:
    query_doc = _make_document(title="Query doc")
    strong_match = _make_document(title="Strong match")
    weak_match = _make_document(title="Weak match")
    assert query_doc.current_version is not None

    embedding_row = DocumentVectorEmbedding(
        document_version_id=query_doc.current_version.id, status=AiAnalysisStatus.SUCCEEDED, embedding=[0.1]
    )
    embeddings = _FakeEmbeddingRepository(
        embedding_by_version_id={query_doc.current_version.id: embedding_row},
        similar_results=[(strong_match.id, 0.9), (weak_match.id, 0.5)],
    )
    documents = _FakeDocumentRepository(
        document_by_id={query_doc.id: query_doc, strong_match.id: strong_match, weak_match.id: weak_match}
    )
    service = SimilarityService(embeddings, documents)

    results = service.find_similar_documents(query_doc.id, organization_id=ORG_ID, min_similarity=0.8)

    assert [doc.title for doc, _ in results] == ["Strong match"]


def test_returns_empty_when_all_matches_below_min_similarity() -> None:
    query_doc = _make_document(title="Query doc")
    weak_match = _make_document(title="Weak match")
    assert query_doc.current_version is not None

    embedding_row = DocumentVectorEmbedding(
        document_version_id=query_doc.current_version.id, status=AiAnalysisStatus.SUCCEEDED, embedding=[0.1]
    )
    embeddings = _FakeEmbeddingRepository(
        embedding_by_version_id={query_doc.current_version.id: embedding_row},
        similar_results=[(weak_match.id, 0.5)],
    )
    documents = _FakeDocumentRepository(document_by_id={query_doc.id: query_doc, weak_match.id: weak_match})
    service = SimilarityService(embeddings, documents)

    assert service.find_similar_documents(query_doc.id, organization_id=ORG_ID, min_similarity=0.8) == []


def test_default_threshold_falls_back_to_settings() -> None:
    """Omitting min_similarity should still filter — falls back to
    settings.similarity_min_score rather than showing everything. Uses a
    score far below any sane configured default so this doesn't need to
    hardcode (and stay in sync with) the exact configured value."""
    query_doc = _make_document(title="Query doc")
    weak_match = _make_document(title="Weak match")
    assert query_doc.current_version is not None

    embedding_row = DocumentVectorEmbedding(
        document_version_id=query_doc.current_version.id, status=AiAnalysisStatus.SUCCEEDED, embedding=[0.1]
    )
    embeddings = _FakeEmbeddingRepository(
        embedding_by_version_id={query_doc.current_version.id: embedding_row},
        similar_results=[(weak_match.id, 0.01)],
    )
    documents = _FakeDocumentRepository(document_by_id={query_doc.id: query_doc, weak_match.id: weak_match})
    service = SimilarityService(embeddings, documents)

    assert service.find_similar_documents(query_doc.id, organization_id=ORG_ID) == []
