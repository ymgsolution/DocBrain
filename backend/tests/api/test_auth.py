"""Auth is mock-identity (pick a user, no password) but with real JWT
mechanics — signed, expiring, verified on every request. These cover the
*mechanics*, which are production-shaped even though the identity source
isn't."""

from fastapi.testclient import TestClient

from app.db.models import User


def test_login_returns_a_working_token(client: TestClient, employee: User) -> None:
    response = client.post("/api/v1/auth/login", json={"email": employee.email})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == employee.email
    assert body["user"]["role"] == "EMPLOYEE"
    assert body["token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == str(employee.id)


def test_login_is_case_insensitive_on_email(client: TestClient, employee: User) -> None:
    response = client.post("/api/v1/auth/login", json={"email": employee.email.upper()})
    assert response.status_code == 200


def test_login_rejects_an_unknown_email(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "nobody@test.docbrain"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_rejects_a_deactivated_user(client: TestClient, db_session, employee: User) -> None:
    employee.is_active = False
    db_session.flush()

    response = client.post("/api/v1/auth/login", json={"email": employee.email})
    assert response.status_code == 401


def test_protected_endpoint_rejects_a_missing_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_protected_endpoint_rejects_a_garbage_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401
