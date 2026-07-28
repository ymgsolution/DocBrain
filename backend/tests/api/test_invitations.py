"""Invite-only signup.

An invitation is the only way an account comes into existence, so the
negative cases are the point: a token must work exactly once, must not
survive expiry or revocation, must not let the accepter choose their own
role or email, and must not be creatable by anyone but an admin.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.models import Invitation, User
from tests.constants import TEST_PASSWORD

NEW_PASSWORD = "AnotherGood1!"


def _invite(client: TestClient, headers: dict, email: str = "new.joiner@test.docbrain", **kwargs) -> dict:
    response = client.post(
        "/api/v1/invitations", headers=headers, json={"email": email, **kwargs}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _accept(client: TestClient, token: str, name: str = "New Joiner", password: str = NEW_PASSWORD):
    return client.post(
        f"/api/v1/public/invitations/{token}/accept",
        json={"displayName": name, "password": password},
    )


def test_an_admin_can_invite_and_the_link_is_returned_once(client: TestClient, auth, admin: User):
    body = _invite(client, auth(admin))

    assert body["token"]
    assert body["url"].endswith(f"/invite/{body['token']}")
    assert body["status"] == "pending"
    assert body["role"] == "EMPLOYEE"


def test_the_token_is_not_returned_when_listing(client: TestClient, auth, admin: User):
    _invite(client, auth(admin))

    listed = client.get("/api/v1/invitations", headers=auth(admin)).json()

    assert "token" not in listed[0]
    assert "url" not in listed[0]


def test_the_token_is_stored_only_as_a_hash(client: TestClient, auth, admin: User, db_session):
    created = _invite(client, auth(admin))

    stored = db_session.get(Invitation, uuid.UUID(created["id"]))

    assert stored.token_hash != created["token"]
    assert len(stored.token_hash) == 64


def test_accepting_creates_a_working_account(client: TestClient, auth, admin: User):
    token = _invite(client, auth(admin))["token"]

    peek = client.get(f"/api/v1/public/invitations/{token}")
    assert peek.status_code == 200
    assert peek.json()["email"] == "new.joiner@test.docbrain"

    accepted = _accept(client, token)
    assert accepted.status_code == 201
    assert accepted.json()["email"] == "new.joiner@test.docbrain"

    # ...and the new account can actually sign in with the chosen password
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "new.joiner@test.docbrain", "password": NEW_PASSWORD},
    )
    assert login.status_code == 200


def test_the_invited_role_is_applied_not_the_default(client: TestClient, auth, admin: User):
    token = _invite(client, auth(admin), role="REVIEWER")["token"]

    _accept(client, token)

    login = client.post(
        "/api/v1/auth/login", json={"email": "new.joiner@test.docbrain", "password": NEW_PASSWORD}
    )
    assert login.json()["user"]["role"] == "REVIEWER"


def test_an_invitation_works_exactly_once(client: TestClient, auth, admin: User):
    token = _invite(client, auth(admin))["token"]
    assert _accept(client, token).status_code == 201

    second = _accept(client, token, name="Impostor")

    assert second.status_code == 404
    assert client.get(f"/api/v1/public/invitations/{token}").status_code == 404


def test_an_expired_invitation_is_rejected(client: TestClient, auth, admin: User, db_session):
    created = _invite(client, auth(admin))
    invitation = db_session.get(Invitation, uuid.UUID(created["id"]))
    invitation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.flush()

    assert client.get(f"/api/v1/public/invitations/{created['token']}").status_code == 404
    assert _accept(client, created["token"]).status_code == 404


def test_a_revoked_invitation_stops_working_immediately(client: TestClient, auth, admin: User):
    created = _invite(client, auth(admin))
    assert client.get(f"/api/v1/public/invitations/{created['token']}").status_code == 200

    revoked = client.delete(f"/api/v1/invitations/{created['id']}", headers=auth(admin))

    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert _accept(client, created["token"]).status_code == 404


def test_every_rejection_looks_the_same_to_an_outsider(client: TestClient, auth, admin: User):
    """Unknown, revoked and already-used tokens must be indistinguishable."""
    created = _invite(client, auth(admin))
    client.delete(f"/api/v1/invitations/{created['id']}", headers=auth(admin))

    unknown = client.get("/api/v1/public/invitations/never-issued-token")
    revoked = client.get(f"/api/v1/public/invitations/{created['token']}")

    assert unknown.status_code == revoked.status_code == 404
    assert unknown.json()["error"]["message"] == revoked.json()["error"]["message"]


def test_the_accepter_cannot_choose_their_own_role_or_email(client: TestClient, auth, admin: User):
    """Both come from the invitation, never the request body — otherwise an
    invited employee could hand themselves ADMIN on the way in."""
    token = _invite(client, auth(admin), role="EMPLOYEE")["token"]

    response = client.post(
        f"/api/v1/public/invitations/{token}/accept",
        json={
            "displayName": "Sneaky",
            "password": NEW_PASSWORD,
            "role": "ADMIN",
            "email": "attacker@evil.test",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "EMPLOYEE"
    assert response.json()["email"] == "new.joiner@test.docbrain"


def test_a_weak_password_is_rejected(client: TestClient, auth, admin: User):
    token = _invite(client, auth(admin))["token"]

    assert _accept(client, token, password="short").status_code == 422
    # ...and the invite survives, so a typo doesn't burn the link
    assert client.get(f"/api/v1/public/invitations/{token}").status_code == 200


def test_inviting_an_existing_email_is_rejected(client: TestClient, auth, admin: User, employee: User):
    response = client.post(
        "/api/v1/invitations", headers=auth(admin), json={"email": employee.email}
    )
    assert response.status_code == 409


def test_a_duplicate_pending_invitation_is_rejected(client: TestClient, auth, admin: User):
    _invite(client, auth(admin))

    response = client.post(
        "/api/v1/invitations", headers=auth(admin), json={"email": "new.joiner@test.docbrain"}
    )
    assert response.status_code == 409


def test_only_an_admin_can_invite(client: TestClient, auth, employee: User, reviewer: User):
    for user in (employee, reviewer):
        response = client.post(
            "/api/v1/invitations", headers=auth(user), json={"email": "someone@test.docbrain"}
        )
        assert response.status_code == 403, f"{user.role} should not be able to invite"


def test_only_an_admin_can_list_or_revoke(client: TestClient, auth, admin: User, employee: User):
    created = _invite(client, auth(admin))

    assert client.get("/api/v1/invitations", headers=auth(employee)).status_code == 403
    assert client.delete(f"/api/v1/invitations/{created['id']}", headers=auth(employee)).status_code == 403


def test_managing_invitations_requires_a_session_at_all(client: TestClient):
    assert client.post("/api/v1/invitations", json={"email": "x@test.docbrain"}).status_code == 401
    assert client.get("/api/v1/invitations").status_code == 401


def test_an_accepted_invitation_cannot_be_revoked(client: TestClient, auth, admin: User):
    """Revoking after acceptance would imply the account disappears, which it
    doesn't — deactivating the user is the real action."""
    created = _invite(client, auth(admin))
    _accept(client, created["token"])

    response = client.delete(f"/api/v1/invitations/{created['id']}", headers=auth(admin))

    assert response.status_code == 422


def test_the_new_account_gets_no_session_from_accepting(client: TestClient, auth, admin: User):
    """Accepting returns the user but sets no cookie and issues no token —
    session creation stays on the single, well-tested login path."""
    token = _invite(client, auth(admin))["token"]

    response = _accept(client, token)

    assert "token" not in response.json()
    assert not response.cookies


def test_an_invited_user_cannot_log_in_before_accepting(client: TestClient, auth, admin: User):
    _invite(client, auth(admin))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "new.joiner@test.docbrain", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
