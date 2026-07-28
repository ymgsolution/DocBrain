"""Password reset.

The defining property here is that "forgot password" must reveal nothing.
An unknown address, a deactivated account and a real one all have to
produce the same response — otherwise the endpoint becomes a way to
discover who has an account.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import PasswordResetToken, User
from tests.constants import TEST_PASSWORD

NEW_PASSWORD = "BrandNewPass1!"


def _request(client: TestClient, email: str):
    return client.post("/api/v1/auth/password-reset", json={"email": email})


def _token_from(emails) -> str:
    """Pulls the token out of the emailed link, the way a real user would."""
    assert emails.sent, "no email was sent"
    text = emails.sent[-1]["text"]
    return text.split("/reset-password/")[1].split()[0].strip()


def test_a_reset_link_is_emailed_and_works(client: TestClient, employee: User, emails):
    assert _request(client, employee.email).status_code == 202

    token = _token_from(emails)
    assert client.post(f"/api/v1/auth/password-reset/{token}", json={"password": NEW_PASSWORD}).status_code == 204

    # the new password works...
    assert client.post(
        "/api/v1/auth/login", json={"email": employee.email, "password": NEW_PASSWORD}
    ).status_code == 200
    # ...and the old one no longer does
    assert client.post(
        "/api/v1/auth/login", json={"email": employee.email, "password": TEST_PASSWORD}
    ).status_code == 401


def test_an_unknown_email_looks_identical_to_a_real_one(client: TestClient, employee: User, emails):
    """The property that stops this being an account-enumeration tool."""
    real = _request(client, employee.email)
    fake = _request(client, "nobody@test.docbrain")

    assert real.status_code == fake.status_code == 202
    assert real.json() == fake.json()


def test_no_email_is_sent_for_an_unknown_address(client: TestClient, emails):
    _request(client, "nobody@test.docbrain")
    assert emails.sent == []


def test_a_deactivated_user_gets_no_reset_link(client: TestClient, db_session, employee: User, emails):
    employee.is_active = False
    db_session.flush()

    assert _request(client, employee.email).status_code == 202
    assert emails.sent == []


def test_a_reset_token_works_only_once(client: TestClient, employee: User, emails):
    _request(client, employee.email)
    token = _token_from(emails)

    assert client.post(f"/api/v1/auth/password-reset/{token}", json={"password": NEW_PASSWORD}).status_code == 204
    second = client.post(f"/api/v1/auth/password-reset/{token}", json={"password": "YetAnother1!"})

    assert second.status_code == 404


def test_requesting_again_invalidates_the_previous_link(client: TestClient, employee: User, emails):
    """Otherwise two live tokens exist, and the older email — possibly the
    one an attacker already has — would still work."""
    _request(client, employee.email)
    first_token = _token_from(emails)

    _request(client, employee.email)
    second_token = _token_from(emails)
    assert first_token != second_token

    assert client.post(
        f"/api/v1/auth/password-reset/{first_token}", json={"password": NEW_PASSWORD}
    ).status_code == 404
    assert client.post(
        f"/api/v1/auth/password-reset/{second_token}", json={"password": NEW_PASSWORD}
    ).status_code == 204


def test_an_expired_token_is_rejected(client: TestClient, db_session, employee: User, emails):
    _request(client, employee.email)
    token = _token_from(emails)

    row = db_session.scalars(
        select(PasswordResetToken).where(PasswordResetToken.user_id == employee.id)
    ).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.flush()

    assert client.post(
        f"/api/v1/auth/password-reset/{token}", json={"password": NEW_PASSWORD}
    ).status_code == 404


def test_an_unknown_token_is_rejected(client: TestClient):
    response = client.post("/api/v1/auth/password-reset/never-issued", json={"password": NEW_PASSWORD})
    assert response.status_code == 404


def test_a_weak_new_password_is_rejected(client: TestClient, employee: User, emails):
    _request(client, employee.email)
    token = _token_from(emails)

    assert client.post(f"/api/v1/auth/password-reset/{token}", json={"password": "short"}).status_code == 422
    # the token survives a typo
    assert client.post(
        f"/api/v1/auth/password-reset/{token}", json={"password": NEW_PASSWORD}
    ).status_code == 204


def test_the_token_is_stored_only_as_a_hash(client: TestClient, db_session, employee: User, emails):
    _request(client, employee.email)
    token = _token_from(emails)

    stored = db_session.scalars(
        select(PasswordResetToken).where(PasswordResetToken.user_id == employee.id)
    ).one()

    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_resetting_does_not_create_a_session(client: TestClient, employee: User, emails):
    """The user returns to the login page and signs in with what they just
    set — session creation stays on one well-tested path."""
    _request(client, employee.email)
    token = _token_from(emails)

    response = client.post(f"/api/v1/auth/password-reset/{token}", json={"password": NEW_PASSWORD})

    assert response.status_code == 204
    assert not response.cookies


def test_the_email_contains_a_usable_link_in_both_bodies(client: TestClient, employee: User, emails):
    _request(client, employee.email)

    message = emails.sent[-1]
    assert message["to"] == employee.email
    assert "/reset-password/" in message["html"]
    assert "/reset-password/" in message["text"]


def test_requesting_a_reset_needs_no_session(client: TestClient, employee: User):
    """Someone who's forgotten their password cannot be signed in."""
    assert _request(client, employee.email).status_code == 202


def test_an_unrelated_uuid_is_not_a_token(client: TestClient):
    response = client.post(f"/api/v1/auth/password-reset/{uuid.uuid4()}", json={"password": NEW_PASSWORD})
    assert response.status_code == 404
