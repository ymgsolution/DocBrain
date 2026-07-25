"""Version history — append-only, with "which one is current" tracked on the
document. Restore deliberately creates a *new* version from an old one's
bytes rather than moving a pointer backwards, so history stays intact."""

import io

from fastapi.testclient import TestClient

from app.db.models import User


def test_uploading_a_new_version_makes_it_current(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    document = upload(headers, title="Safety Policy", content=b"version one text")

    response = client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        data={"changeNote": "Updated the evacuation section"},
        files={"file": ("policy-v2.txt", io.BytesIO(b"version two text"), "text/plain")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["versionNumber"] == 2
    assert response.json()["isCurrent"] is True

    detail = client.get(f"/api/v1/documents/{document['id']}", headers=headers).json()
    assert detail["currentVersion"]["versionNumber"] == 2
    assert detail["versionCount"] == 2


def test_version_upload_requires_a_meaningful_change_note(
    client: TestClient, auth, employee: User, upload
) -> None:
    headers = auth(employee)
    document = upload(headers)

    response = client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        data={"changeNote": "x"},  # below the 5-character minimum
        files={"file": ("notes.txt", io.BytesIO(b"content"), "text/plain")},
    )

    assert response.status_code == 422


def test_listing_versions_returns_newest_state_correctly(
    client: TestClient, auth, employee: User, upload
) -> None:
    headers = auth(employee)
    document = upload(headers, content=b"first")
    client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        data={"changeNote": "Second revision"},
        files={"file": ("second.txt", io.BytesIO(b"second"), "text/plain")},
    )

    response = client.get(f"/api/v1/documents/{document['id']}/versions", headers=headers)

    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 2
    current = [v for v in versions if v["isCurrent"]]
    assert len(current) == 1
    assert current[0]["versionNumber"] == 2


def test_downloading_a_version_returns_that_versions_bytes(
    client: TestClient, auth, employee: User, upload
) -> None:
    headers = auth(employee)
    document = upload(headers, content=b"the original content")
    client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        data={"changeNote": "Replaced the content"},
        files={"file": ("newer.txt", io.BytesIO(b"the replacement content"), "text/plain")},
    )

    v1 = client.get(f"/api/v1/documents/{document['id']}/versions/1/content", headers=headers)
    v2 = client.get(f"/api/v1/documents/{document['id']}/versions/2/content", headers=headers)

    assert v1.content == b"the original content"
    assert v2.content == b"the replacement content"
    assert "attachment" in v1.headers["content-disposition"]


def test_inline_disposition_is_used_for_previewable_types(
    client: TestClient, auth, employee: User, upload
) -> None:
    headers = auth(employee)
    document = upload(headers)

    response = client.get(
        f"/api/v1/documents/{document['id']}/versions/1/content",
        headers=headers,
        params={"disposition": "inline"},
    )

    assert "inline" in response.headers["content-disposition"]


def test_restoring_an_old_version_creates_a_new_one_with_its_content(
    client: TestClient, auth, employee: User, upload
) -> None:
    headers = auth(employee)
    document = upload(headers, content=b"the original content")
    client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        data={"changeNote": "Replaced the content"},
        files={"file": ("newer.txt", io.BytesIO(b"the replacement content"), "text/plain")},
    )

    response = client.post(
        f"/api/v1/documents/{document['id']}/versions/1/restore",
        headers=headers,
        json={"changeNote": "Reverting to the original"},
    )

    assert response.status_code == 201, response.text
    restored = response.json()
    assert restored["versionNumber"] == 3  # a new version, not a rewind
    assert restored["restoredFromVersionId"] is not None

    content = client.get(f"/api/v1/documents/{document['id']}/versions/3/content", headers=headers)
    assert content.content == b"the original content"


def test_restoring_the_current_version_is_rejected(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    document = upload(headers)

    response = client.post(
        f"/api/v1/documents/{document['id']}/versions/1/restore",
        headers=headers,
        json={"changeNote": "Pointless restore"},
    )

    assert response.status_code == 422
