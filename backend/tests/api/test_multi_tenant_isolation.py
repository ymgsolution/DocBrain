"""Cross-tenant isolation — the actual proof that one organization can never
see another's data, per docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md.

Every other test file in this suite implicitly runs inside a single
organization (the `make_user`/`category` fixtures default to
DEFAULT_ORGANIZATION_ID), which is exactly why isolation needs its own file:
nothing else in the suite would ever notice a missing `organization_id`
filter, because there was never a second organization's data around to leak.

`other_org_id` is inserted directly via SQL rather than through the API,
since there is no "create organization" endpoint (and shouldn't be one yet —
see Part 12 of the architecture review). Everything else goes through the
real endpoints, same as the rest of the suite, and rolls back with the test.
"""

import io
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Category, DocumentVectorEmbedding, User
from app.db.models.enums import AiAnalysisStatus, UserRole


@pytest.fixture
def other_org_id(db_session: Session) -> uuid.UUID:
    org_id = uuid.uuid4()
    db_session.execute(
        text("INSERT INTO organizations (id, name, slug) VALUES (:id, :name, :slug)"),
        {"id": org_id, "name": "Other Org", "slug": f"other-org-{org_id.hex[:8]}"},
    )
    db_session.flush()
    return org_id


@pytest.fixture
def other_org_admin(make_user, other_org_id: uuid.UUID) -> User:
    return make_user(UserRole.ADMIN, organization_id=other_org_id)


@pytest.fixture
def other_org_employee(make_user, other_org_id: uuid.UUID) -> User:
    return make_user(UserRole.EMPLOYEE, organization_id=other_org_id)


@pytest.fixture
def other_org_category(db_session: Session, other_org_id: uuid.UUID) -> Category:
    suffix = uuid.uuid4().hex[:8]
    row = Category(
        name=f"Other Org Category {suffix}",
        slug=f"other-org-category-{suffix}",
        organization_id=other_org_id,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _upload(client: TestClient, headers: dict, category_id: uuid.UUID, *, title: str) -> dict:
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": title, "categoryId": str(category_id), "tags": ""},
        files={"file": ("notes.txt", io.BytesIO(b"secret contents"), "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- documents ---------------------------------------------------------


def test_list_documents_excludes_another_orgs_documents(
    client: TestClient, auth, employee: User, category: Category, other_org_employee: User, other_org_category: Category
) -> None:
    _upload(client, auth(other_org_employee), other_org_category.id, title="Other Org Secret")
    _upload(client, auth(employee), category.id, title="My Own Doc")

    response = client.get("/api/v1/documents", headers=auth(employee))
    assert response.status_code == 200
    titles = [d["title"] for d in response.json()["items"]]
    assert "Other Org Secret" not in titles
    assert "My Own Doc" in titles


def test_get_document_by_id_404s_across_orgs(
    client: TestClient, auth, employee: User, other_org_employee: User, other_org_category: Category
) -> None:
    other_doc = _upload(client, auth(other_org_employee), other_org_category.id, title="Other Org Secret")

    response = client.get(f"/api/v1/documents/{other_doc['id']}", headers=auth(employee))
    assert response.status_code == 404


def test_cannot_update_another_orgs_document(
    client: TestClient, auth, admin: User, other_org_employee: User, other_org_category: Category
) -> None:
    other_doc = _upload(client, auth(other_org_employee), other_org_category.id, title="Other Org Secret")

    response = client.patch(
        f"/api/v1/documents/{other_doc['id']}", headers=auth(admin), json={"title": "Hijacked"}
    )
    assert response.status_code == 404


def test_cannot_delete_another_orgs_document(
    client: TestClient, auth, admin: User, other_org_employee: User, other_org_category: Category
) -> None:
    other_doc = _upload(client, auth(other_org_employee), other_org_category.id, title="Other Org Secret")

    response = client.delete(f"/api/v1/documents/{other_doc['id']}", headers=auth(admin))
    assert response.status_code == 404


# --- similarity (the highest-risk fix in the whole migration) ---------


def test_similar_documents_never_returns_another_orgs_document(
    client: TestClient,
    auth,
    db_session: Session,
    employee: User,
    category: Category,
    other_org_employee: User,
    other_org_category: Category,
) -> None:
    """Two documents, identical embedding vectors (the strongest possible
    case — an unscoped nearest-neighbor query would rank the other org's
    document first). Embeddings are inserted directly since generating them
    for real requires the AI worker and a live Gemini call."""
    mine = _upload(client, auth(employee), category.id, title="My Query Doc")
    theirs = _upload(client, auth(other_org_employee), other_org_category.id, title="Their Near-Identical Doc")

    vector = [0.42] * 768
    db_session.add(
        DocumentVectorEmbedding(
            document_version_id=uuid.UUID(mine["currentVersion"]["id"]),
            organization_id=employee.organization_id,
            status=AiAnalysisStatus.SUCCEEDED,
            embedding=vector,
            embedding_model="test",
            embedding_dimension=768,
        )
    )
    db_session.add(
        DocumentVectorEmbedding(
            document_version_id=uuid.UUID(theirs["currentVersion"]["id"]),
            organization_id=other_org_employee.organization_id,
            status=AiAnalysisStatus.SUCCEEDED,
            embedding=vector,
            embedding_model="test",
            embedding_dimension=768,
        )
    )
    db_session.flush()

    response = client.get(f"/api/v1/documents/{mine['id']}/similar", headers=auth(employee))
    assert response.status_code == 200
    result_ids = [d["id"] for d in response.json()]
    assert theirs["id"] not in result_ids


# --- taxonomy -----------------------------------------------------------


def test_list_categories_excludes_another_orgs_categories(
    client: TestClient, auth, employee: User, category: Category, other_org_category: Category
) -> None:
    response = client.get("/api/v1/categories", headers=auth(employee))
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert str(other_org_category.id) not in ids
    assert str(category.id) in ids


def test_cannot_delete_another_orgs_category(client: TestClient, auth, admin: User, other_org_category: Category) -> None:
    response = client.delete(f"/api/v1/categories/{other_org_category.id}", headers=auth(admin))
    assert response.status_code == 404


# --- reviews --------------------------------------------------------------


def test_pending_reviews_excludes_another_orgs_documents(
    client: TestClient,
    auth,
    db_session: Session,
    reviewer: User,
    admin: User,
    category: Category,
    other_org_admin: User,
    other_org_category: Category,
) -> None:
    mine = _upload(client, auth(admin), category.id, title="My Overdue Doc")
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their Overdue Doc")

    from app.db.models import Document

    db_session.query(Document).filter(Document.id == uuid.UUID(mine["id"])).update(
        {"review_due_date": date.today() - timedelta(days=1)}
    )
    db_session.query(Document).filter(Document.id == uuid.UUID(theirs["id"])).update(
        {"review_due_date": date.today() - timedelta(days=1)}
    )
    db_session.flush()

    response = client.get("/api/v1/reviews/pending", headers=auth(reviewer))
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Their Overdue Doc" not in titles
    assert "My Overdue Doc" in titles


# --- dashboard --------------------------------------------------------------


def test_dashboard_totals_exclude_another_orgs_documents(
    client: TestClient, auth, employee: User, category: Category, other_org_employee: User, other_org_category: Category
) -> None:
    before = client.get("/api/v1/dashboard/summary", headers=auth(employee))
    assert before.status_code == 200
    before_total = before.json()["totals"]["totalDocuments"]

    _upload(client, auth(other_org_employee), other_org_category.id, title="Their Doc")

    after = client.get("/api/v1/dashboard/summary", headers=auth(employee))
    assert after.status_code == 200
    assert after.json()["totals"]["totalDocuments"] == before_total


# --- shares -----------------------------------------------------------------


def test_cannot_create_share_link_for_another_orgs_document(
    client: TestClient, auth, admin: User, other_org_employee: User, other_org_category: Category
) -> None:
    other_doc = _upload(client, auth(other_org_employee), other_org_category.id, title="Their Doc")

    response = client.post(
        f"/api/v1/documents/{other_doc['id']}/shares", headers=auth(admin), json={"expiresInDays": 7}
    )
    assert response.status_code == 404


# --- admin user management (the last-admin lockout must be per-org) --------


def test_cannot_deactivate_another_orgs_user(client: TestClient, auth, admin: User, other_org_employee: User) -> None:
    response = client.post(f"/api/v1/admin/users/{other_org_employee.id}/deactivate", headers=auth(admin))
    assert response.status_code == 404


def test_cannot_change_role_of_another_orgs_user(client: TestClient, auth, admin: User, other_org_employee: User) -> None:
    response = client.patch(
        f"/api/v1/admin/users/{other_org_employee.id}/role", headers=auth(admin), json={"role": "ADMIN"}
    )
    assert response.status_code == 404


def test_admin_user_list_excludes_another_orgs_users(
    client: TestClient, auth, admin: User, other_org_employee: User
) -> None:
    response = client.get("/api/v1/admin/users?status=all", headers=auth(admin))
    assert response.status_code == 200
    ids = [u["id"] for u in response.json()["items"]]
    assert str(other_org_employee.id) not in ids


def test_colleague_directory_excludes_another_orgs_users(
    client: TestClient, auth, employee: User, other_org_employee: User
) -> None:
    response = client.get("/api/v1/auth/users", headers=auth(employee))
    assert response.status_code == 200
    ids = [u["id"] for u in response.json()]
    assert str(other_org_employee.id) not in ids


# --- invitations --------------------------------------------------------


def test_invitation_list_excludes_another_orgs_invitations(
    client: TestClient, auth, admin: User, other_org_admin: User
) -> None:
    other_invite = client.post(
        "/api/v1/invitations",
        headers=auth(other_org_admin),
        json={"email": f"invitee-{uuid.uuid4().hex[:8]}@test.docbrain", "role": "EMPLOYEE", "expiresInDays": 7},
    )
    assert other_invite.status_code == 201, other_invite.text

    response = client.get("/api/v1/invitations", headers=auth(admin))
    assert response.status_code == 200
    ids = [i["id"] for i in response.json()]
    assert other_invite.json()["id"] not in ids


def test_invitation_accept_assigns_inviting_admins_organization(
    client: TestClient, auth, other_org_admin: User, other_org_id: uuid.UUID
) -> None:
    email = f"new-hire-{uuid.uuid4().hex[:8]}@test.docbrain"
    invite = client.post(
        "/api/v1/invitations",
        headers=auth(other_org_admin),
        json={"email": email, "role": "EMPLOYEE", "expiresInDays": 7},
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]

    accept = client.post(
        f"/api/v1/public/invitations/{token}/accept",
        json={"displayName": "New Hire", "password": "a-strong-password-123"},
    )
    assert accept.status_code == 201, accept.text
    assert accept.json()["organization"]["id"] == str(other_org_id)


# --- versions ----------------------------------------------------------


def test_cannot_list_another_orgs_document_versions(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their versioned doc")

    response = client.get(f"/api/v1/documents/{theirs['id']}/versions", headers=auth(admin))
    assert response.status_code == 404, response.text


def test_cannot_upload_a_version_onto_another_orgs_document(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their doc")

    response = client.post(
        f"/api/v1/documents/{theirs['id']}/versions",
        headers=auth(admin),
        data={"changeNote": "not mine to change"},
        files={"file": ("notes.txt", io.BytesIO(b"intruding"), "text/plain")},
    )
    assert response.status_code == 404, response.text


def test_cannot_download_another_orgs_version_content(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    """The one that would leak actual file bytes rather than metadata."""
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their doc")

    response = client.get(f"/api/v1/documents/{theirs['id']}/versions/1/content", headers=auth(admin))
    assert response.status_code == 404, response.text
    assert b"secret contents" not in response.content


def test_cannot_restore_another_orgs_version(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their doc")
    second = client.post(
        f"/api/v1/documents/{theirs['id']}/versions",
        headers=auth(other_org_admin),
        data={"changeNote": "their second revision"},
        files={"file": ("notes.txt", io.BytesIO(b"their v2"), "text/plain")},
    )
    assert second.status_code == 201, second.text

    response = client.post(
        f"/api/v1/documents/{theirs['id']}/versions/1/restore", headers=auth(admin), json={}
    )
    assert response.status_code == 404, response.text


# --- tags --------------------------------------------------------------


def test_tag_vocabularies_are_per_organization(
    client: TestClient, auth, admin: User, category: Category, other_org_admin: User, other_org_category: Category
) -> None:
    """Tags moved from globally unique to unique *per organization* in the
    Phase 4 migration, so the same tag name must be able to exist in two
    organizations as two independent rows."""
    shared_name = f"shared-{uuid.uuid4().hex[:8]}"

    mine = client.post(
        "/api/v1/documents",
        headers=auth(admin),
        data={"title": "Mine", "categoryId": str(category.id), "tags": shared_name},
        files={"file": ("notes.txt", io.BytesIO(b"mine"), "text/plain")},
    )
    assert mine.status_code == 201, mine.text
    theirs = client.post(
        "/api/v1/documents",
        headers=auth(other_org_admin),
        data={"title": "Theirs", "categoryId": str(other_org_category.id), "tags": shared_name},
        files={"file": ("notes.txt", io.BytesIO(b"theirs"), "text/plain")},
    )
    assert theirs.status_code == 201, theirs.text

    my_tag_ids = {t["id"] for t in mine.json()["tags"]}
    their_tag_ids = {t["id"] for t in theirs.json()["tags"]}
    assert my_tag_ids and their_tag_ids
    assert my_tag_ids.isdisjoint(their_tag_ids), "the same tag name reused one row across organizations"


def test_list_tags_excludes_another_orgs_tags(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    their_tag = f"theirtag-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/documents",
        headers=auth(other_org_admin),
        data={"title": "Theirs", "categoryId": str(other_org_category.id), "tags": their_tag},
        files={"file": ("notes.txt", io.BytesIO(b"theirs"), "text/plain")},
    )
    assert created.status_code == 201, created.text

    listed = client.get("/api/v1/tags", headers=auth(admin))
    assert listed.status_code == 200, listed.text
    assert their_tag not in {t["name"] for t in listed.json()}


# --- trash -------------------------------------------------------------


def test_trash_excludes_another_orgs_deleted_documents(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their doomed doc")
    assert client.delete(f"/api/v1/documents/{theirs['id']}", headers=auth(other_org_admin)).status_code == 204

    listed = client.get("/api/v1/documents/trash", headers=auth(admin))
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert theirs["id"] not in {d["id"] for d in body.get("items", body)}


def test_cannot_restore_or_purge_another_orgs_trashed_document(
    client: TestClient, auth, admin: User, other_org_admin: User, other_org_category: Category
) -> None:
    theirs = _upload(client, auth(other_org_admin), other_org_category.id, title="Their doomed doc")
    assert client.delete(f"/api/v1/documents/{theirs['id']}", headers=auth(other_org_admin)).status_code == 204

    assert client.post(f"/api/v1/documents/{theirs['id']}/restore", headers=auth(admin)).status_code == 404
    assert client.delete(f"/api/v1/documents/{theirs['id']}/permanent", headers=auth(admin)).status_code == 404


# --- ownership reassignment --------------------------------------------


def test_cannot_reassign_a_document_to_another_orgs_user(
    client: TestClient, auth, admin: User, category: Category, other_org_employee: User
) -> None:
    """PATCH used to write owner_id straight onto the row with no lookup, so a
    user id from another tenant would transfer the document across the
    isolation boundary and render that person's name and email here."""
    mine = _upload(client, auth(admin), category.id, title="Mine")

    response = client.patch(
        f"/api/v1/documents/{mine['id']}", headers=auth(admin), json={"ownerId": str(other_org_employee.id)}
    )
    assert response.status_code == 422, response.text

    unchanged = client.get(f"/api/v1/documents/{mine['id']}", headers=auth(admin)).json()
    assert unchanged["owner"]["id"] == str(admin.id)


def test_cannot_reassign_a_document_to_a_nonexistent_user(
    client: TestClient, auth, admin: User, category: Category
) -> None:
    """Previously an IntegrityError on the FK, surfacing as a 500 because
    error_handlers only maps DomainError/RequestValidationError."""
    mine = _upload(client, auth(admin), category.id, title="Mine")

    response = client.patch(
        f"/api/v1/documents/{mine['id']}", headers=auth(admin), json={"ownerId": str(uuid.uuid4())}
    )
    assert response.status_code == 422, response.text


def test_reassigning_to_a_colleague_in_the_same_organization_still_works(
    client: TestClient, auth, admin: User, employee: User, category: Category
) -> None:
    """The guard must not break the legitimate case."""
    mine = _upload(client, auth(admin), category.id, title="Mine")

    response = client.patch(
        f"/api/v1/documents/{mine['id']}", headers=auth(admin), json={"ownerId": str(employee.id)}
    )
    assert response.status_code == 200, response.text
    assert response.json()["owner"]["id"] == str(employee.id)
