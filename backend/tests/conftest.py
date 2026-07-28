"""Shared fixtures for the API test suite.

Every test runs inside a real Postgres transaction that is rolled back when
the test finishes. That means tests exercise the genuine schema — the
search_vector/version_count/tags.usage_count triggers, Postgres enums, FK
cascades, real full-text search — rather than an approximation, while
leaving zero trace in the database afterwards.

This is why there's no separate test database, no Docker, and no new
prerequisite for running the suite: SQLAlchemy's
join_transaction_mode="create_savepoint" contains the services' own
db.commit() calls (they commit constantly) inside the outer transaction, so
one rollback at the end undoes everything. Verified: a full upload →
search → download flow through the real app leaves 0 rows behind.

SQLite-in-memory isn't an option here — the schema leans on tsvector, ARRAY,
pgvector, Postgres enums and triggers throughout.
"""

import logging
import uuid
from collections.abc import Iterator
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Category, User
from app.core.passwords import hash_password
from app.db.models.enums import UserRole
from app.main import app
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.router import get_document_service
from app.modules.documents.service import DocumentService
from app.modules.versions.repository import VersionRepository
from app.modules.versions.router import get_document_service as get_document_service_for_versions
from app.modules.versions.router import get_version_service
from app.modules.shares.repository import ShareLinkRepository
from app.modules.shares.router import get_share_service
from app.modules.shares.service import ShareService
from app.modules.versions.service import VersionService
from app.storage.local_adapter import LocalFileSystemStorage

# Every test user shares this; individual tests that care about wrong
# passwords pass something else explicitly.
TEST_PASSWORD = "Test@123"

# The app's own logging config sets INFO, which makes httpx narrate every
# single test request. Tests are noisy enough without it.
logging.getLogger("httpx").setLevel(logging.WARNING)


@pytest.fixture
def db_session() -> Iterator[Session]:
    if not get_settings().database_url:
        pytest.skip("DATABASE_URL not configured — API tests need a real Postgres.")

    # Imported here, not at module scope: app.db.session builds an engine at
    # import time, which would blow up collection of the pure-unit tests
    # (tests/ai, tests/text_extraction) on a machine with no DATABASE_URL.
    from app.db.session import engine

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def storage(tmp_path) -> LocalFileSystemStorage:
    """Local disk under pytest's tmp_path, never the configured provider —
    tests must not read or write the real Supabase bucket."""
    return LocalFileSystemStorage(root=str(tmp_path))


@pytest.fixture
def client(db_session: Session, storage: LocalFileSystemStorage) -> Iterator[TestClient]:
    from app.db.session import get_db_session

    def _session_override() -> Session:
        return db_session

    def _document_service() -> DocumentService:
        return DocumentService(DocumentRepository(db_session), storage)

    def _version_service() -> VersionService:
        return VersionService(VersionRepository(db_session), storage)

    def _share_service() -> ShareService:
        return ShareService(ShareLinkRepository(db_session), DocumentRepository(db_session), storage)

    app.dependency_overrides[get_db_session] = _session_override
    # documents/ and versions/ each define their own get_document_service;
    # dependency_overrides keys on the function object, so both need one.
    app.dependency_overrides[get_document_service] = _document_service
    app.dependency_overrides[get_document_service_for_versions] = _document_service
    app.dependency_overrides[get_version_service] = _version_service
    app.dependency_overrides[get_share_service] = _share_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session: Session):
    """Creates a user with a given role. A factory rather than a plain
    fixture so a test needing a *second* employee (permission checks) can
    ask for one without a near-duplicate fixture per role."""

    def _make(role: UserRole) -> User:
        suffix = uuid.uuid4().hex[:8]
        user = User(
            email=f"{role.value.lower()}-{suffix}@test.docbrain",
            display_name=f"Test {role.value.title()} {suffix}",
            role=role,
            is_active=True,
            password_hash=hash_password(TEST_PASSWORD),
        )
        db_session.add(user)
        db_session.flush()
        return user

    return _make


@pytest.fixture
def employee(make_user) -> User:
    return make_user(UserRole.EMPLOYEE)


@pytest.fixture
def reviewer(make_user) -> User:
    return make_user(UserRole.REVIEWER)


@pytest.fixture
def admin(make_user) -> User:
    return make_user(UserRole.ADMIN)


@pytest.fixture
def today() -> date:
    """Today according to **UTC**, which is the clock the app itself uses
    (`datetime.now(timezone.utc).date()` in reviews/service.py).

    Not `date.today()`: that's the machine's local date, and for any timezone
    ahead of UTC the two disagree for the first hours of the day — which is
    exactly how this was found, when review tests started failing at
    00:00 IST because the app said the 25th and the test said the 26th."""
    return datetime.now(timezone.utc).date()


@pytest.fixture
def category(db_session: Session) -> Category:
    suffix = uuid.uuid4().hex[:8]
    row = Category(name=f"Test Category {suffix}", slug=f"test-category-{suffix}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def auth(client: TestClient):
    """Logs a user in through the real /auth/login endpoint (real signed JWT,
    verified on every subsequent request) rather than forging a header."""

    def _headers(user: User) -> dict[str, str]:
        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return _headers


def text_file(name: str = "notes.txt", content: bytes = b"Some document content for testing.") -> dict:
    """A real file payload — libmagic sniffs the bytes for real during upload,
    so the content has to genuinely match the extension."""
    import io

    return {"file": (name, io.BytesIO(content), "text/plain")}


@pytest.fixture
def upload(client: TestClient, category: Category):
    """Uploads a document through the real POST /documents endpoint."""

    def _upload(headers: dict[str, str], *, title: str = "Test Document", tags: str = "", **kwargs) -> dict:
        response = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": title, "categoryId": str(category.id), "tags": tags},
            files=text_file(**kwargs),
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _upload
