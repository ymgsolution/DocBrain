"""Admin user management — deactivation, reactivation and role changes.

The interesting assertions here are not "the flag flipped". They are:

  * a deactivated person's *already-issued* token stops working on the very
    next request, because that is what "revoke access" has to mean;
  * the two ways an admin can lock the workspace out of its own
    administration are refused (deactivating/demoting yourself, and doing it
    to the last remaining admin);
  * revoking someone also revokes the share links they sent out, which is
    the difference between losing an account and losing your reach.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.exceptions import ValidationError
from app.db.models import PasswordResetToken, User
from app.db.models.enums import UserRole
from app.modules.users.repository import UserAdminRepository
from app.modules.users.service import UserAdminService
from tests.constants import TEST_PASSWORD

USERS = "/api/v1/admin/users"


@pytest.fixture
def sole_admin(db_session, admin: User) -> User:
    """Makes `admin` the only active admin *within this test's transaction*.

    The suite runs against the real database inside a savepoint that is
    rolled back afterwards, so the workspace's genuine admin accounts are
    present in every query — which would mean count_active_admins never
    reaches zero and the last-admin guard could never be exercised. Flipping
    them here is confined to the transaction and undone on rollback.
    """
    others = db_session.scalars(
        select(User).where(
            User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != admin.id
        )
    ).all()
    for other in others:
        other.is_active = False
    db_session.flush()
    return admin


def test_an_admin_can_list_users(client: TestClient, auth, admin: User):
    body = client.get(USERS, headers=auth(admin)).json()

    assert body["page"] == 0
    assert body["total"] >= 1
    assert any(u["id"] == str(admin.id) for u in body["items"])


def test_a_non_admin_cannot_list_users(client: TestClient, auth, employee: User, reviewer: User):
    assert client.get(USERS, headers=auth(employee)).status_code == 403
    assert client.get(USERS, headers=auth(reviewer)).status_code == 403


def test_listing_requires_a_session_at_all(client: TestClient):
    assert client.get(USERS).status_code == 401


def test_search_matches_display_name_and_email(client: TestClient, auth, admin: User, employee: User):
    headers = auth(admin)

    by_name = client.get(USERS, headers=headers, params={"search": employee.display_name}).json()
    by_email = client.get(USERS, headers=headers, params={"search": employee.email}).json()

    assert [u["id"] for u in by_name["items"]] == [str(employee.id)]
    assert [u["id"] for u in by_email["items"]] == [str(employee.id)]


def test_search_treats_wildcards_as_literal_text(client: TestClient, auth, admin: User, employee: User):
    """An unescaped % in the search box would match every user, which reads
    as "search is broken" — or worse, as a way to page through everyone
    while looking like a narrow query."""
    body = client.get(USERS, headers=auth(admin), params={"search": "%"}).json()

    assert body["total"] == 0


def test_deactivated_users_are_hidden_by_default_and_findable_on_request(
    client: TestClient, auth, admin: User, employee: User
):
    headers = auth(admin)
    client.post(f"{USERS}/{employee.id}/deactivate", headers=headers)

    active = client.get(USERS, headers=headers, params={"search": employee.email}).json()
    inactive = client.get(
        USERS, headers=headers, params={"search": employee.email, "status": "inactive"}
    ).json()
    every = client.get(USERS, headers=headers, params={"search": employee.email, "status": "all"}).json()

    assert active["total"] == 0
    assert [u["id"] for u in inactive["items"]] == [str(employee.id)]
    assert [u["id"] for u in every["items"]] == [str(employee.id)]


def test_the_colleague_directory_never_exposes_deactivated_people(
    client: TestClient, auth, admin: User, employee: User
):
    """/auth/users is readable by every signed-in user. Deactivating someone
    must remove them from it, not just from the admin screen."""
    headers = auth(admin)
    client.post(f"{USERS}/{employee.id}/deactivate", headers=headers)

    directory = client.get("/api/v1/auth/users", headers=headers).json()

    assert all(u["id"] != str(employee.id) for u in directory)


def test_deactivating_kills_an_already_issued_token_immediately(
    client: TestClient, auth, admin: User, employee: User
):
    """The whole point. Their JWT is still valid for hours — it must stop
    being accepted on the next request regardless."""
    victim_headers = auth(employee)
    assert client.get("/api/v1/auth/me", headers=victim_headers).status_code == 200

    client.post(f"{USERS}/{employee.id}/deactivate", headers=auth(admin))

    assert client.get("/api/v1/auth/me", headers=victim_headers).status_code == 401


def test_a_deactivated_user_cannot_log_back_in(client: TestClient, auth, admin: User, employee: User):
    client.post(f"{USERS}/{employee.id}/deactivate", headers=auth(admin))

    response = client.post(
        "/api/v1/auth/login", json={"email": employee.email, "password": TEST_PASSWORD}
    )

    assert response.status_code == 401


def test_deactivating_records_who_did_it_and_when(client: TestClient, auth, admin: User, employee: User):
    body = client.post(f"{USERS}/{employee.id}/deactivate", headers=auth(admin)).json()

    assert body["isActive"] is False
    assert body["deactivatedAt"] is not None
    assert body["deactivatedBy"]["id"] == str(admin.id)


def test_deactivating_invalidates_outstanding_password_reset_links(
    client: TestClient, auth, admin: User, employee: User, db_session
):
    client.post("/api/v1/public/auth/password-reset", json={"email": employee.email})
    outstanding = db_session.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == employee.id, PasswordResetToken.used_at.is_(None)
        )
    ).all()
    assert len(outstanding) == 1

    client.post(f"{USERS}/{employee.id}/deactivate", headers=auth(admin))
    db_session.expire_all()

    still_live = db_session.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == employee.id, PasswordResetToken.used_at.is_(None)
        )
    ).all()
    assert still_live == []


def test_deactivating_twice_is_harmless(client: TestClient, auth, admin: User, employee: User):
    headers = auth(admin)
    first = client.post(f"{USERS}/{employee.id}/deactivate", headers=headers).json()
    second = client.post(f"{USERS}/{employee.id}/deactivate", headers=headers)

    assert second.status_code == 200
    # The audit stamp records the moment access was cut, and must not be
    # overwritten by a second click hours later.
    assert second.json()["deactivatedAt"] == first["deactivatedAt"]


def test_an_admin_cannot_deactivate_themselves(client: TestClient, auth, admin: User):
    response = client.post(f"{USERS}/{admin.id}/deactivate", headers=auth(admin))

    assert response.status_code == 422
    assert "your own account" in response.json()["error"]["message"]
    assert client.get("/api/v1/auth/me", headers=auth(admin)).status_code == 200


def test_one_of_two_admins_can_be_deactivated(
    client: TestClient, auth, sole_admin: User, make_user, db_session
):
    """The permitted case, and the one that makes the guard's condition
    matter: with a second admin present, removing one is fine."""
    other_admin = make_user(UserRole.ADMIN)
    db_session.flush()

    response = client.post(f"{USERS}/{other_admin.id}/deactivate", headers=auth(sole_admin))

    assert response.status_code == 200
    assert response.json()["isActive"] is False


def test_the_workspace_cannot_be_left_without_an_active_admin(
    client: TestClient, auth, sole_admin: User
):
    """The invariant that actually protects the workspace, asserted through
    the only route that can reach it.

    A caller must be an active admin to get past require_role, so whenever
    the target is the last active admin the caller *is* that person — and the
    self-check refuses first. That is what keeps the count above zero; the
    separate last-admin guard below it is unreachable from the API and is
    covered at the service level instead.
    """
    response = client.post(f"{USERS}/{sole_admin.id}/deactivate", headers=auth(sole_admin))

    assert response.status_code == 422
    assert client.get("/api/v1/auth/me", headers=auth(sole_admin)).status_code == 200


def test_the_last_admin_guard_holds_for_callers_that_skip_the_role_check(
    sole_admin: User, make_user, db_session
):
    """Exercised at the service, because no HTTP caller can reach it.

    The guard is there for entry points that don't go through require_role —
    a maintenance script or a future CLI — where the actor need not be an
    active admin and the self-check therefore wouldn't fire.
    """
    service = UserAdminService(UserAdminRepository(db_session))
    script_actor = make_user(UserRole.ADMIN)
    script_actor.is_active = False  # stands in for a non-interactive caller
    db_session.flush()

    with pytest.raises(ValidationError, match="last active admin"):
        service.deactivate(sole_admin.id, actor=script_actor)

    with pytest.raises(ValidationError, match="last active admin"):
        service.change_role(sole_admin.id, role=UserRole.EMPLOYEE, actor=script_actor)


def test_reactivating_restores_access(client: TestClient, auth, admin: User, employee: User):
    headers = auth(admin)
    client.post(f"{USERS}/{employee.id}/deactivate", headers=headers)
    assert (
        client.post("/api/v1/auth/login", json={"email": employee.email, "password": TEST_PASSWORD}).status_code
        == 401
    )

    body = client.post(f"{USERS}/{employee.id}/reactivate", headers=headers).json()

    assert body["isActive"] is True
    assert body["deactivatedAt"] is None
    assert body["deactivatedBy"] is None
    assert (
        client.post("/api/v1/auth/login", json={"email": employee.email, "password": TEST_PASSWORD}).status_code
        == 200
    )


def test_deactivating_an_unknown_user_is_a_404(client: TestClient, auth, admin: User):
    response = client.post(f"{USERS}/{uuid.uuid4()}/deactivate", headers=auth(admin))

    assert response.status_code == 404


def test_a_non_admin_cannot_deactivate_anyone(client: TestClient, auth, employee: User, reviewer: User):
    response = client.post(f"{USERS}/{reviewer.id}/deactivate", headers=auth(employee))

    assert response.status_code == 403


# --- role changes -----------------------------------------------------------


def test_an_admin_can_change_someone_s_role(client: TestClient, auth, admin: User, employee: User):
    body = client.patch(f"{USERS}/{employee.id}/role", headers=auth(admin), json={"role": "REVIEWER"}).json()

    assert body["role"] == "REVIEWER"


def test_a_promoted_user_immediately_gains_the_new_role_s_access(
    client: TestClient, auth, admin: User, employee: User
):
    """Reviews is reviewer-and-above, so it's the cheapest proof that the
    change takes effect on the next request rather than the next login."""
    assert client.get("/api/v1/reviews/pending", headers=auth(employee)).status_code == 403

    client.patch(f"{USERS}/{employee.id}/role", headers=auth(admin), json={"role": "REVIEWER"})

    assert client.get("/api/v1/reviews/pending", headers=auth(employee)).status_code == 200


def test_a_demoted_user_immediately_loses_access(client: TestClient, auth, admin: User, make_user, db_session):
    target = make_user(UserRole.REVIEWER)
    db_session.flush()
    assert client.get("/api/v1/reviews/pending", headers=auth(target)).status_code == 200

    client.patch(f"{USERS}/{target.id}/role", headers=auth(admin), json={"role": "EMPLOYEE"})

    assert client.get("/api/v1/reviews/pending", headers=auth(target)).status_code == 403


def test_an_admin_cannot_change_their_own_role(client: TestClient, auth, admin: User):
    response = client.patch(f"{USERS}/{admin.id}/role", headers=auth(admin), json={"role": "EMPLOYEE"})

    assert response.status_code == 422
    assert "your own role" in response.json()["error"]["message"]


def test_one_of_two_admins_can_be_demoted(
    client: TestClient, auth, sole_admin: User, make_user, db_session
):
    other_admin = make_user(UserRole.ADMIN)
    db_session.flush()

    response = client.patch(
        f"{USERS}/{other_admin.id}/role", headers=auth(sole_admin), json={"role": "EMPLOYEE"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "EMPLOYEE"


def test_an_invalid_role_is_rejected(client: TestClient, auth, admin: User, employee: User):
    response = client.patch(f"{USERS}/{employee.id}/role", headers=auth(admin), json={"role": "SUPERUSER"})

    assert response.status_code == 422


def test_a_non_admin_cannot_change_roles(client: TestClient, auth, employee: User, reviewer: User):
    response = client.patch(f"{USERS}/{reviewer.id}/role", headers=auth(employee), json={"role": "ADMIN"})

    assert response.status_code == 403


# --- reach: share links -----------------------------------------------------


def test_deactivating_someone_kills_the_share_links_they_sent_out(
    client: TestClient, auth, admin: User, employee: User, upload
):
    """Losing the account but not the links would leave a former employee's
    URLs serving company documents to whoever they were sent to."""
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = client.post(
        f"/api/v1/documents/{document['id']}/shares", headers=headers, json={"expiresInDays": 7}
    ).json()["token"]
    assert client.get(f"/api/v1/public/shares/{token}").status_code == 200

    client.post(f"{USERS}/{employee.id}/deactivate", headers=auth(admin))

    assert client.get(f"/api/v1/public/shares/{token}").status_code == 404
    assert client.get(f"/api/v1/public/shares/{token}/content").status_code == 404


def test_reactivating_someone_restores_their_share_links(
    client: TestClient, auth, admin: User, employee: User, upload
):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = client.post(
        f"/api/v1/documents/{document['id']}/shares", headers=headers, json={"expiresInDays": 7}
    ).json()["token"]

    client.post(f"{USERS}/{employee.id}/deactivate", headers=auth(admin))
    client.post(f"{USERS}/{employee.id}/reactivate", headers=auth(admin))

    assert client.get(f"/api/v1/public/shares/{token}").status_code == 200
