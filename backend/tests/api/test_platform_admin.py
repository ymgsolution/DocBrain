"""Platform admin — the Super Admin feature. Two things matter most here:

  * a platform admin token and a regular user token must never be
    interchangeable, in either direction;
  * the organization list must expose counts only, never document titles
    or content — proven by actually creating a document and checking it
    never appears in the response body, not just checking the schema.

The end-to-end bootstrap flow (create org -> create its first admin -> that
admin logs in through the *regular* login -> lands in a genuinely empty,
isolated workspace) is the real point of this feature, so it gets its own
test rather than just unit-testing the pieces separately.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.db.models import PlatformAdmin, User

PLATFORM_LOGIN = "/api/v1/platform/auth/login"
PLATFORM_ME = "/api/v1/platform/auth/me"
ORGANIZATIONS = "/api/v1/platform/organizations"

PLATFORM_PASSWORD = "PlatformPass123"


@pytest.fixture
def platform_admin(db_session: Session) -> PlatformAdmin:
    suffix = uuid.uuid4().hex[:8]
    admin = PlatformAdmin(
        email=f"platform-{suffix}@test.docbrain",
        display_name=f"Platform Admin {suffix}",
        password_hash=hash_password(PLATFORM_PASSWORD),
    )
    db_session.add(admin)
    db_session.flush()
    return admin


def _platform_auth(client: TestClient, admin: PlatformAdmin) -> dict[str, str]:
    response = client.post(PLATFORM_LOGIN, json={"email": admin.email, "password": PLATFORM_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# --- login ---------------------------------------------------------------


def test_platform_admin_can_log_in(client: TestClient, platform_admin: PlatformAdmin) -> None:
    response = client.post(PLATFORM_LOGIN, json={"email": platform_admin.email, "password": PLATFORM_PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["admin"]["email"] == platform_admin.email
    assert "token" in body


def test_wrong_password_is_rejected(client: TestClient, platform_admin: PlatformAdmin) -> None:
    response = client.post(PLATFORM_LOGIN, json={"email": platform_admin.email, "password": "wrong"})
    assert response.status_code == 401


def test_unknown_email_is_rejected(client: TestClient) -> None:
    response = client.post(PLATFORM_LOGIN, json={"email": "nobody@test.docbrain", "password": "whatever123"})
    assert response.status_code == 401


def test_inactive_platform_admin_cannot_log_in(client: TestClient, db_session: Session) -> None:
    admin = PlatformAdmin(
        email="inactive-platform@test.docbrain",
        display_name="Inactive",
        password_hash=hash_password(PLATFORM_PASSWORD),
        is_active=False,
    )
    db_session.add(admin)
    db_session.flush()

    response = client.post(PLATFORM_LOGIN, json={"email": admin.email, "password": PLATFORM_PASSWORD})
    assert response.status_code == 401


# --- the two auth systems are not interchangeable -------------------------


def test_platform_token_is_rejected_by_regular_auth_me(
    client: TestClient, platform_admin: PlatformAdmin
) -> None:
    headers = _platform_auth(client, platform_admin)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


def test_regular_user_token_is_rejected_by_platform_me(client: TestClient, auth, employee: User) -> None:
    response = client.get(PLATFORM_ME, headers=auth(employee))
    assert response.status_code == 401


def test_regular_user_token_is_rejected_by_organizations_list(client: TestClient, auth, admin: User) -> None:
    """Even a regular ADMIN — the highest role that exists inside an
    organization — must not reach platform endpoints."""
    response = client.get(ORGANIZATIONS, headers=auth(admin))
    assert response.status_code == 401


def test_organizations_list_requires_a_platform_token_at_all(client: TestClient) -> None:
    response = client.get(ORGANIZATIONS)
    assert response.status_code == 401


# --- organization list exposes counts only, never content -----------------


def test_organization_list_shows_counts_but_never_document_content(
    client: TestClient, auth, platform_admin: PlatformAdmin, employee: User, category
) -> None:
    secret_title = f"Confidential Merger Plan {uuid.uuid4().hex[:8]}"
    upload = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": secret_title, "categoryId": str(category.id), "tags": ""},
        files={"file": ("notes.txt", io.BytesIO(b"contents"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text

    headers = _platform_auth(client, platform_admin)
    response = client.get(ORGANIZATIONS, headers=headers)
    assert response.status_code == 200

    body_text = response.text
    assert secret_title not in body_text, "document title leaked into the platform organization list!"

    accenture = next(o for o in response.json() if o["id"] == str(employee.organization_id))
    assert accenture["documentCount"] >= 1
    assert accenture["userCount"] >= 1
    # The only per-org fields are id/name/slug/createdAt + the three counts —
    # nothing else, by construction of OrganizationStats, but assert it here
    # too so a future field addition has to consciously pass this test.
    assert set(accenture.keys()) == {
        "id",
        "name",
        "slug",
        "createdAt",
        "userCount",
        "activeUserCount",
        "documentCount",
    }


# --- the full bootstrap flow -----------------------------------------------


def test_create_organization_and_first_admin_end_to_end(client: TestClient, platform_admin: PlatformAdmin) -> None:
    headers = _platform_auth(client, platform_admin)

    org_name = f"Infosys {uuid.uuid4().hex[:8]}"
    create_org = client.post(ORGANIZATIONS, headers=headers, json={"name": org_name})
    assert create_org.status_code == 201, create_org.text
    org = create_org.json()
    assert org["name"] == org_name

    admin_email = f"admin-{uuid.uuid4().hex[:8]}@infosys.example"
    create_admin = client.post(
        f"{ORGANIZATIONS}/{org['id']}/admins",
        headers=headers,
        json={"email": admin_email, "displayName": "Infosys Admin", "password": "InfosysPass123"},
    )
    assert create_admin.status_code == 201, create_admin.text
    assert create_admin.json()["email"] == admin_email

    # The new admin logs in through the REGULAR login, not the platform one.
    login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": "InfosysPass123"})
    assert login.status_code == 200, login.text
    new_admin_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    me = client.get("/api/v1/auth/me", headers=new_admin_headers)
    assert me.status_code == 200
    assert me.json()["organization"]["id"] == org["id"]
    assert me.json()["role"] == "ADMIN"

    documents = client.get("/api/v1/documents", headers=new_admin_headers)
    assert documents.status_code == 200
    assert documents.json()["total"] == 0, "a brand new organization must start with zero documents"

    # The actual reported bug: a new org's category dropdown must not be
    # empty, or the very first upload is silently blocked
    # (docs/ORGANIZATION-MIGRATION-BUG-INVESTIGATION.md).
    categories = client.get("/api/v1/categories", headers=new_admin_headers)
    assert categories.status_code == 200
    category_names = [c["name"] for c in categories.json()]
    assert category_names, "a brand new organization must not start with zero categories"
    assert "General" in category_names

    # Prove it end-to-end, not just that a category row exists: actually
    # upload a document using one of the seeded categories.
    first_category_id = categories.json()[0]["id"]
    upload = client.post(
        "/api/v1/documents",
        headers=new_admin_headers,
        data={"title": "Welcome Packet", "categoryId": first_category_id, "tags": ""},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text


def test_new_organization_starts_with_default_categories_only_visible_to_it(
    client: TestClient, auth, platform_admin: PlatformAdmin, employee: User
) -> None:
    headers = _platform_auth(client, platform_admin)
    create_org = client.post(ORGANIZATIONS, headers=headers, json={"name": f"Org {uuid.uuid4().hex[:8]}"})
    org_id = create_org.json()["id"]

    create_admin = client.post(
        f"{ORGANIZATIONS}/{org_id}/admins",
        headers=headers,
        json={
            "email": f"admin-{uuid.uuid4().hex[:8]}@test.docbrain",
            "displayName": "New Org Admin",
            "password": "SomePassword123",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": create_admin.json()["email"], "password": "SomePassword123"},
    )
    new_org_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    response = client.get("/api/v1/categories", headers=new_org_headers)
    assert response.status_code == 200
    new_org_categories = response.json()
    assert sorted(c["name"] for c in new_org_categories) == ["Finance", "General", "HR", "Legal", "Operations"]
    new_org_category_ids = {c["id"] for c in new_org_categories}

    # Names can legitimately repeat across organizations (composite
    # uniqueness is per-org, e.g. both orgs may have a "Finance" category) —
    # what must never repeat is the *row*. Assert by id, not name.
    accenture_categories = client.get("/api/v1/categories", headers=auth(employee))
    accenture_category_ids = {c["id"] for c in accenture_categories.json()}
    assert new_org_category_ids.isdisjoint(accenture_category_ids)


def test_cannot_create_second_first_admin_with_duplicate_email(
    client: TestClient, platform_admin: PlatformAdmin, employee: User
) -> None:
    """Email is a global uniqueness key (one User row per address across
    every organization), same rule the invitation accept flow enforces."""
    headers = _platform_auth(client, platform_admin)
    create_org = client.post(ORGANIZATIONS, headers=headers, json={"name": f"Org {uuid.uuid4().hex[:8]}"})
    org_id = create_org.json()["id"]

    response = client.post(
        f"{ORGANIZATIONS}/{org_id}/admins",
        headers=headers,
        json={"email": employee.email, "displayName": "Duplicate", "password": "SomePassword123"},
    )
    assert response.status_code == 409


def test_create_first_admin_requires_platform_token(client: TestClient, auth, admin: User) -> None:
    response = client.post(
        f"{ORGANIZATIONS}/{uuid.uuid4()}/admins",
        headers=auth(admin),
        json={"email": "someone@test.docbrain", "displayName": "Someone", "password": "SomePassword123"},
    )
    assert response.status_code == 401
