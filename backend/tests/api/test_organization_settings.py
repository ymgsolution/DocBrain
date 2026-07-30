"""Organization Settings — Phase 1 (the data exists and is readable).

Two things are worth proving here rather than assuming.

First, that a new organization gets working settings *without anyone having
to create them*. These are NOT NULL columns with a server_default precisely
so there is no "settings row" to forget, and this project has already shipped
three bugs of the opposite shape (a new organization with no categories, then
categories with no review period, then AI rows with no organization_id).

Second, that storage usage counts what it claims to count: every version's
bytes, including superseded versions and documents sitting in Trash. Those
files really are still on disk — soft delete only flips Document.status, and
only a permanent delete removes them — so a number that quietly excluded them
would disagree with the disk.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.db.models import Category, PlatformAdmin, User
from app.db.models.organization import (
    DEFAULT_AI_SUGGESTIONS_ENABLED,
    DEFAULT_DUPLICATE_DETECTION_ENABLED,
    DEFAULT_STORAGE_LIMIT_MB,
)
from app.modules.documents.repository import DocumentRepository

ORGANIZATIONS = "/api/v1/platform/organizations"
PLATFORM_PASSWORD = "PlatformPass123"


@pytest.fixture
def platform_admin(db_session: Session) -> PlatformAdmin:
    admin = PlatformAdmin(
        email=f"settings-{uuid.uuid4().hex[:8]}@platform.docbrain",
        display_name="Settings Platform Admin",
        password_hash=hash_password(PLATFORM_PASSWORD),
        is_active=True,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


def _platform_auth(client: TestClient, admin: PlatformAdmin) -> dict[str, str]:
    response = client.post(
        "/api/v1/platform/auth/login", json={"email": admin.email, "password": PLATFORM_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_new_organization_gets_working_settings_without_anyone_creating_them(
    client: TestClient, platform_admin: PlatformAdmin
) -> None:
    headers = _platform_auth(client, platform_admin)
    created = client.post(ORGANIZATIONS, headers=headers, json={"name": f"Org {uuid.uuid4().hex[:8]}"})
    assert created.status_code == 201, created.text

    listed = client.get(ORGANIZATIONS, headers=headers).json()
    organization = next(o for o in listed if o["id"] == created.json()["id"])

    assert organization["settings"]["aiSuggestionsEnabled"] is DEFAULT_AI_SUGGESTIONS_ENABLED
    assert organization["settings"]["duplicateDetectionEnabled"] is DEFAULT_DUPLICATE_DETECTION_ENABLED
    assert organization["settings"]["storageLimitMb"] == DEFAULT_STORAGE_LIMIT_MB
    # Brand new organization, so nothing stored yet — and 0, never null.
    assert organization["storageUsedBytes"] == 0


def test_storage_usage_counts_every_version_not_just_the_current_one(
    client: TestClient, auth, employee: User, category: Category, db_session: Session
) -> None:
    """Version history is append-only and every version's file stays on disk,
    so a second version must add to usage rather than replace the first."""
    repository = DocumentRepository(db_session)
    before = repository.storage_used_bytes(employee.organization_id)

    v1 = b"first version contents"
    upload = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "Versioned", "categoryId": str(category.id)},
        files={"file": ("doc.txt", io.BytesIO(v1), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["id"]
    after_v1 = repository.storage_used_bytes(employee.organization_id)
    assert after_v1 == before + len(v1)

    v2 = b"second version contents, longer than the first"
    new_version = client.post(
        f"/api/v1/documents/{document_id}/versions",
        headers=auth(employee),
        data={"changeNote": "second"},
        files={"file": ("doc.txt", io.BytesIO(v2), "text/plain")},
    )
    assert new_version.status_code == 201, new_version.text

    # Both versions counted — not just the current one.
    assert repository.storage_used_bytes(employee.organization_id) == before + len(v1) + len(v2)


def test_storage_usage_still_counts_documents_in_trash(
    client: TestClient, auth, admin: User, category: Category, db_session: Session
) -> None:
    """Soft delete flips Document.status but leaves the file on disk, so the
    bytes must keep counting. Only a permanent delete frees space — the
    behaviour the Trash screen has to explain to users.

    Uses an admin rather than an employee because permanent delete is
    admin-only, and this test needs to reach that final step to prove the
    bytes are released.
    """
    repository = DocumentRepository(db_session)
    before = repository.storage_used_bytes(admin.organization_id)

    content = b"this document is going to the trash"
    upload = client.post(
        "/api/v1/documents",
        headers=auth(admin),
        data={"title": "Doomed", "categoryId": str(category.id)},
        files={"file": ("doomed.txt", io.BytesIO(content), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["id"]
    assert repository.storage_used_bytes(admin.organization_id) == before + len(content)

    trashed = client.delete(f"/api/v1/documents/{document_id}", headers=auth(admin))
    assert trashed.status_code == 204, trashed.text

    # Still counted: the file is untouched, the row is merely marked DELETED.
    assert repository.storage_used_bytes(admin.organization_id) == before + len(content)

    purged = client.delete(f"/api/v1/documents/{document_id}/permanent", headers=auth(admin))
    assert purged.status_code == 204, purged.text

    # Now the bytes are genuinely gone.
    assert repository.storage_used_bytes(admin.organization_id) == before


def test_storage_usage_is_per_organization(
    client: TestClient, auth, employee: User, category: Category, db_session: Session
) -> None:
    """One organization's uploads must never count against another's limit.

    The second organization is inserted with raw SQL rather than through the
    platform endpoint, matching test_multi_tenant_isolation.py — it only
    needs to exist as a row to be summed against.
    """
    repository = DocumentRepository(db_session)
    other_org_id = uuid.uuid4()
    db_session.execute(
        text("INSERT INTO organizations (id, name, slug) VALUES (:id, :name, :slug)"),
        {"id": other_org_id, "name": "Other Org", "slug": f"other-{other_org_id.hex[:8]}"},
    )
    db_session.flush()

    before_other = repository.storage_used_bytes(other_org_id)
    upload = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "Mine", "categoryId": str(category.id)},
        files={"file": ("mine.txt", io.BytesIO(b"some bytes here"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text

    assert repository.storage_used_bytes(other_org_id) == before_other


def test_ai_settings_travel_with_the_logged_in_user(client: TestClient, auth, employee: User) -> None:
    """The app needs these on first paint to tell "no suggestion yet" apart
    from "suggestions are switched off" — the two look identical in the
    document payload."""
    response = client.get("/api/v1/auth/me", headers=auth(employee))
    assert response.status_code == 200, response.text

    organization = response.json()["organization"]
    assert organization["aiSuggestionsEnabled"] is True
    assert organization["duplicateDetectionEnabled"] is True
    # Never exposed to a tenant: only /platform may see or change the limit.
    assert "storageLimitMb" not in organization
