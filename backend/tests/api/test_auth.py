"""Real password authentication.

The negative cases matter most here. In particular, every failed login must
be indistinguishable from every other: if "no such account" and "wrong
password" differ in wording, status, or noticeably in timing, the endpoint
becomes a way to discover which email addresses have accounts.
"""

from fastapi.testclient import TestClient

from app.core.passwords import hash_password
from app.db.models import User
from tests.conftest import TEST_PASSWORD


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_with_the_right_password_returns_a_working_token(client: TestClient, employee: User) -> None:
    response = _login(client, employee.email, TEST_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == employee.email
    assert body["token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == str(employee.id)


def test_login_is_case_insensitive_on_email(client: TestClient, employee: User) -> None:
    assert _login(client, employee.email.upper(), TEST_PASSWORD).status_code == 200


def test_login_rejects_the_wrong_password(client: TestClient, employee: User) -> None:
    assert _login(client, employee.email, "not-the-password").status_code == 401


def test_login_rejects_an_unknown_email(client: TestClient) -> None:
    assert _login(client, "nobody@test.docbrain", TEST_PASSWORD).status_code == 401


def test_a_wrong_password_is_indistinguishable_from_an_unknown_account(
    client: TestClient, employee: User
) -> None:
    """The property that stops this endpoint being used to enumerate which
    emails are registered."""
    wrong_password = _login(client, employee.email, "not-the-password")
    unknown_email = _login(client, "nobody@test.docbrain", TEST_PASSWORD)

    assert wrong_password.status_code == unknown_email.status_code
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]
    assert wrong_password.json()["error"]["code"] == unknown_email.json()["error"]["code"]


def test_login_rejects_a_deactivated_user(client: TestClient, db_session, employee: User) -> None:
    employee.is_active = False
    db_session.flush()

    assert _login(client, employee.email, TEST_PASSWORD).status_code == 401


def test_a_user_with_no_password_cannot_log_in(client: TestClient, db_session, employee: User) -> None:
    """An invited user exists before they've set a password. Until they
    accept, their account must not be reachable — including by sending an
    empty password, which some hashers would otherwise treat as a match."""
    employee.password_hash = None
    db_session.flush()

    assert _login(client, employee.email, TEST_PASSWORD).status_code == 401
    assert _login(client, employee.email, "").status_code == 422  # rejected before it reaches the service


def test_login_requires_a_password_field_at_all(client: TestClient, employee: User) -> None:
    response = client.post("/api/v1/auth/login", json={"email": employee.email})
    assert response.status_code == 422


def test_the_user_list_now_requires_a_session(client: TestClient, auth, employee: User) -> None:
    """It used to be completely open — anyone could enumerate every user's
    name, email and role. It still exists (the Pending Reviews owner filter
    needs it), but only for someone already signed in."""
    assert client.get("/api/v1/auth/users").status_code == 401

    response = client.get("/api/v1/auth/users", headers=auth(employee))
    assert response.status_code == 200
    assert any(u["email"] == employee.email for u in response.json())


def test_passwords_are_hashed_not_stored(db_session, employee: User) -> None:
    assert employee.password_hash != TEST_PASSWORD
    assert employee.password_hash.startswith("$argon2")


def test_the_same_password_hashes_differently_each_time() -> None:
    """Per-hash salting: two users with the same password must not share a
    hash, or one cracked hash would expose every account using it."""
    assert hash_password(TEST_PASSWORD) != hash_password(TEST_PASSWORD)


def test_protected_endpoints_still_reject_missing_and_garbage_tokens(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
