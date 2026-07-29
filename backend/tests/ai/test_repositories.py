"""Regression coverage for the bug where AiDocumentAnalysisRepository and
DocumentVectorEmbeddingRepository.get_or_create() constructed their row
without organization_id, which is NOT NULL as of migration 8ebd25762f70 —
every AI job for every organization (including Accenture's own newest
documents, not just new orgs) crashed with a NotNullViolation the moment it
tried to write its result row. Uses the real /documents upload endpoint
(same real-Postgres db_session fixture as the rest of the suite) so the
DocumentVersion this exercises is exactly what the AI worker sees in
production, not a hand-built stand-in."""

import io
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.analysis_repository import AiDocumentAnalysisRepository
from app.ai.embedding_repository import DocumentVectorEmbeddingRepository
from app.db.models import Category, User


def _upload_version(client: TestClient, auth, employee: User, category: Category) -> uuid.UUID:
    response = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "AI Repo Test Doc", "categoryId": str(category.id)},
        files={"file": ("doc.txt", io.BytesIO(b"Some content for AI processing."), "text/plain")},
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["currentVersion"]["id"])


def test_analysis_repository_get_or_create_stamps_organization_id(
    client: TestClient, auth, employee: User, category: Category, db_session: Session
) -> None:
    version_id = _upload_version(client, auth, employee, category)

    row = AiDocumentAnalysisRepository(db_session).get_or_create(version_id, employee.organization_id)

    assert row.organization_id == employee.organization_id
    assert row.document_version_id == version_id


def test_embedding_repository_get_or_create_stamps_organization_id(
    client: TestClient, auth, employee: User, category: Category, db_session: Session
) -> None:
    version_id = _upload_version(client, auth, employee, category)

    row = DocumentVectorEmbeddingRepository(db_session).get_or_create(version_id, employee.organization_id)

    assert row.organization_id == employee.organization_id
    assert row.document_version_id == version_id


def test_get_or_create_is_idempotent_and_does_not_duplicate_the_row(
    client: TestClient, auth, employee: User, category: Category, db_session: Session
) -> None:
    version_id = _upload_version(client, auth, employee, category)
    repo = AiDocumentAnalysisRepository(db_session)

    first = repo.get_or_create(version_id, employee.organization_id)
    second = repo.get_or_create(version_id, employee.organization_id)

    assert first.id == second.id
