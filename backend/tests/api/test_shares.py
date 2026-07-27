"""External share links — the app's only unauthenticated read path.

The tests that matter most here are the negative ones: an expired link, a
revoked link, a link whose document was deleted, and above all that the
public routes cannot be steered toward a document the token wasn't issued
for. A share feature that works is easy; one that only ever exposes the one
document it should is the actual requirement.
"""

import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.models import ShareLink, User
from app.db.models.enums import UserRole


def _create_link(client: TestClient, headers: dict, document_id: str, days: int = 7) -> dict:
    response = client.post(
        f"/api/v1/documents/{document_id}/shares", headers=headers, json={"expiresInDays": days}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_creating_a_link_returns_a_usable_url_and_token(client: TestClient, auth, employee: User, upload):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")

    body = _create_link(client, headers, document["id"])

    assert body["token"]
    assert body["url"].endswith(f"/share/{body['token']}")
    assert body["isActive"] is True
    assert body["viewCount"] == 0
    assert body["versionNumber"] == 1


def test_the_raw_token_is_never_returned_again(client: TestClient, auth, employee: User, upload):
    """It exists exactly once, in the create response. Losing it means
    revoking and re-issuing — by design, since only the hash is stored."""
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    _create_link(client, headers, document["id"])

    listed = client.get(f"/api/v1/documents/{document['id']}/shares", headers=headers).json()

    assert len(listed) == 1
    assert "token" not in listed[0]
    assert "url" not in listed[0]


def test_the_token_is_not_stored_in_readable_form(client: TestClient, auth, employee: User, upload, db_session):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = _create_link(client, headers, document["id"])["token"]

    stored = db_session.query(ShareLink).one()

    assert stored.token_hash != token
    assert len(stored.token_hash) == 64  # sha256 hex


def test_a_stranger_with_the_link_can_read_the_document(client: TestClient, auth, employee: User, upload):
    """The whole point: no cookie, no Authorization header, no account."""
    headers = auth(employee)
    document = upload(headers, title="Quarterly Report", content=b"the shared file contents")
    token = _create_link(client, headers, document["id"])["token"]

    meta = client.get(f"/api/v1/public/shares/{token}")
    assert meta.status_code == 200
    assert meta.json()["title"] == "Quarterly Report"

    content = client.get(f"/api/v1/public/shares/{token}/content")
    assert content.status_code == 200
    assert content.content == b"the shared file contents"


def test_the_public_view_leaks_no_internal_metadata(client: TestClient, auth, employee: User, upload):
    headers = auth(employee)
    document = upload(headers, title="Quarterly Report", tags="confidential,internal")
    token = _create_link(client, headers, document["id"])["token"]

    body = client.get(f"/api/v1/public/shares/{token}").json()

    for leaked in ("owner", "category", "tags", "id", "documentId", "status", "reviewDueDate"):
        assert leaked not in body, f"public payload exposed {leaked!r}"


def test_shared_content_is_served_inline_and_never_as_a_download(
    client: TestClient, auth, employee: User, upload
):
    """View-only is enforced server-side, so a recipient calling the URL
    directly still cannot turn it into an attachment."""
    headers = auth(employee)
    document = upload(headers, title="View Only Please")
    token = _create_link(client, headers, document["id"])["token"]

    response = client.get(f"/api/v1/public/shares/{token}/content")

    assert "inline" in response.headers["content-disposition"]
    assert "attachment" not in response.headers["content-disposition"]
    assert "noindex" in response.headers["x-robots-tag"]


def test_an_expired_link_is_rejected(client: TestClient, auth, employee: User, upload, db_session):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = _create_link(client, headers, document["id"])["token"]

    db_session.query(ShareLink).one().expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.flush()

    assert client.get(f"/api/v1/public/shares/{token}").status_code == 404
    assert client.get(f"/api/v1/public/shares/{token}/content").status_code == 404


def test_a_revoked_link_stops_working_immediately(client: TestClient, auth, employee: User, upload):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    created = _create_link(client, headers, document["id"])
    token = created["token"]
    assert client.get(f"/api/v1/public/shares/{token}").status_code == 200

    revoked = client.delete(f"/api/v1/documents/{document['id']}/shares/{created['id']}", headers=headers)

    assert revoked.status_code == 200
    assert revoked.json()["isActive"] is False
    assert client.get(f"/api/v1/public/shares/{token}").status_code == 404


def test_a_link_dies_with_its_document(client: TestClient, auth, employee: User, upload):
    """A soft-deleted document must not stay reachable through an old link."""
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = _create_link(client, headers, document["id"])["token"]

    client.delete(f"/api/v1/documents/{document['id']}", headers=headers)

    assert client.get(f"/api/v1/public/shares/{token}").status_code == 404


def test_every_rejection_looks_identical_to_an_outsider(client: TestClient, auth, employee: User, upload):
    """Unknown, expired and revoked tokens must be indistinguishable, or the
    endpoint becomes an oracle for probing which links exist."""
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    created = _create_link(client, headers, document["id"])
    client.delete(f"/api/v1/documents/{document['id']}/shares/{created['id']}", headers=headers)

    unknown = client.get("/api/v1/public/shares/a-token-that-was-never-issued")
    revoked = client.get(f"/api/v1/public/shares/{created['token']}")

    assert unknown.status_code == revoked.status_code == 404
    assert unknown.json()["error"]["message"] == revoked.json()["error"]["message"]


def test_the_pinned_version_does_not_change_when_a_new_one_is_uploaded(
    client: TestClient, auth, employee: User, upload
):
    """The recipient keeps seeing exactly what was sent to them."""
    headers = auth(employee)
    document = upload(headers, title="Pinned Contract", content=b"version one as shared")
    token = _create_link(client, headers, document["id"])["token"]

    client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        data={"changeNote": "Internal revision after sharing"},
        files={"file": ("v2.txt", io.BytesIO(b"version two, internal only"), "text/plain")},
    )

    content = client.get(f"/api/v1/public/shares/{token}/content")

    assert content.content == b"version one as shared"
    assert client.get(f"/api/v1/public/shares/{token}").json()["versionNumber"] == 1


def test_views_are_counted_for_the_owner(client: TestClient, auth, employee: User, upload):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = _create_link(client, headers, document["id"])["token"]

    client.get(f"/api/v1/public/shares/{token}")
    client.get(f"/api/v1/public/shares/{token}")

    listed = client.get(f"/api/v1/documents/{document['id']}/shares", headers=headers).json()
    assert listed[0]["viewCount"] == 2
    assert listed[0]["lastViewedAt"] is not None


def test_another_employee_cannot_share_someone_elses_document(
    client: TestClient, auth, employee: User, make_user, upload
):
    document = upload(auth(employee), title="Private Contract")
    intruder = make_user(UserRole.EMPLOYEE)

    response = client.post(
        f"/api/v1/documents/{document['id']}/shares", headers=auth(intruder), json={"expiresInDays": 7}
    )

    assert response.status_code == 403


def test_another_employee_cannot_revoke_someone_elses_link(
    client: TestClient, auth, employee: User, make_user, upload
):
    headers = auth(employee)
    document = upload(headers, title="Private Contract")
    created = _create_link(client, headers, document["id"])
    intruder = make_user(UserRole.EMPLOYEE)

    response = client.delete(
        f"/api/v1/documents/{document['id']}/shares/{created['id']}", headers=auth(intruder)
    )

    assert response.status_code == 403


def test_a_link_cannot_be_revoked_through_a_different_document(
    client: TestClient, auth, employee: User, upload
):
    """Without the document_id/link_id consistency check, holding any link id
    plus edit rights on any document would be enough to revoke it."""
    headers = auth(employee)
    target = upload(headers, title="Target Document")
    decoy = upload(headers, title="Decoy Document")
    created = _create_link(client, headers, target["id"])

    response = client.delete(f"/api/v1/documents/{decoy['id']}/shares/{created['id']}", headers=headers)

    assert response.status_code == 404
    assert client.get(f"/api/v1/public/shares/{created['token']}").status_code == 200  # still live


def test_expiry_must_be_within_the_allowed_window(client: TestClient, auth, employee: User, upload):
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")

    assert client.post(
        f"/api/v1/documents/{document['id']}/shares", headers=headers, json={"expiresInDays": 0}
    ).status_code == 422
    assert client.post(
        f"/api/v1/documents/{document['id']}/shares", headers=headers, json={"expiresInDays": 3650}
    ).status_code == 422


def test_share_management_still_requires_a_session(client: TestClient, auth, employee: User, upload):
    """Only the two /public/ routes are open; managing links is not."""
    document = upload(auth(employee), title="Contract For Client")

    assert client.post(f"/api/v1/documents/{document['id']}/shares", json={"expiresInDays": 7}).status_code == 401
    assert client.get(f"/api/v1/documents/{document['id']}/shares").status_code == 401


def test_a_share_token_is_not_a_session(client: TestClient, auth, employee: User, upload):
    """The token must not be usable as a credential against the normal API —
    otherwise a share link would quietly become a login."""
    headers = auth(employee)
    document = upload(headers, title="Contract For Client")
    token = _create_link(client, headers, document["id"])["token"]

    bearer = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/documents", headers=bearer).status_code == 401
    assert client.get(f"/api/v1/documents/{document['id']}", headers=bearer).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 401


def test_sharing_an_unknown_document_is_404(client: TestClient, auth, employee: User):
    response = client.post(
        f"/api/v1/documents/{uuid.uuid4()}/shares", headers=auth(employee), json={"expiresInDays": 7}
    )
    assert response.status_code == 404


def test_a_reviewer_may_share_a_document_they_do_not_own(
    client: TestClient, auth, employee: User, reviewer: User, upload
):
    document = upload(auth(employee), title="Reviewer Shareable")

    response = client.post(
        f"/api/v1/documents/{document['id']}/shares", headers=auth(reviewer), json={"expiresInDays": 7}
    )

    assert response.status_code == 201
