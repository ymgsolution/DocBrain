"""Upload, read, search and edit — the core of the app. Uploads go through
the real endpoint with real bytes, so libmagic genuinely sniffs the content
and Postgres genuinely rebuilds search_vector via its trigger."""

import io

from fastapi.testclient import TestClient

from app.db.models import Category, User


def test_upload_creates_a_document_with_version_one(
    client: TestClient, auth, employee: User, category: Category
) -> None:
    response = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "Employee Handbook", "categoryId": str(category.id), "tags": "hr,policy"},
        files={"file": ("handbook.txt", io.BytesIO(b"Company handbook contents."), "text/plain")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Employee Handbook"
    assert body["category"]["id"] == str(category.id)
    assert body["owner"]["id"] == str(employee.id)
    assert body["currentVersion"]["versionNumber"] == 1
    assert body["currentVersion"]["originalFilename"] == "handbook.txt"
    assert body["versionCount"] == 1
    assert sorted(t["name"] for t in body["tags"]) == ["hr", "policy"]


def test_upload_rejects_a_disallowed_extension(
    client: TestClient, auth, employee: User, category: Category
) -> None:
    response = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "Sneaky Binary", "categoryId": str(category.id), "tags": ""},
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00binary"), "application/octet-stream")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_rejects_content_that_contradicts_its_extension(
    client: TestClient, auth, employee: User, category: Category
) -> None:
    """A .pdf that's really plain text — the check that can only be done by
    sniffing the bytes, not by trusting the filename."""
    response = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "Not Really A PDF", "categoryId": str(category.id), "tags": ""},
        files={"file": ("invoice.pdf", io.BytesIO(b"just plain text, not a pdf"), "application/pdf")},
    )

    assert response.status_code == 415


def test_upload_rejects_an_unknown_category(client: TestClient, auth, employee: User) -> None:
    import uuid

    response = client.post(
        "/api/v1/documents",
        headers=auth(employee),
        data={"title": "Orphan Document", "categoryId": str(uuid.uuid4()), "tags": ""},
        files={"file": ("notes.txt", io.BytesIO(b"content"), "text/plain")},
    )

    assert response.status_code == 422


def test_full_text_search_finds_a_document_by_title(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    upload(headers, title="Quarterly Travel Budget")
    upload(headers, title="Fire Safety Procedure")

    response = client.get("/api/v1/documents", headers=headers, params={"q": "quarterly travel"})

    assert response.status_code == 200
    titles = [d["title"] for d in response.json()["items"]]
    assert "Quarterly Travel Budget" in titles
    assert "Fire Safety Procedure" not in titles


def test_search_matches_on_tags_too(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    upload(headers, title="Onboarding Checklist", tags="induction")

    response = client.get("/api/v1/documents", headers=headers, params={"q": "induction"})

    assert [d["title"] for d in response.json()["items"]] == ["Onboarding Checklist"]


def test_get_detail_returns_404_for_an_unknown_document(client: TestClient, auth, employee: User) -> None:
    import uuid

    response = client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=auth(employee))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_owner_can_update_metadata(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    document = upload(headers, title="Draft Title", tags="old")

    response = client.patch(
        f"/api/v1/documents/{document['id']}",
        headers=headers,
        json={"title": "Finalised Title", "tags": ["new", "approved"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Finalised Title"
    assert sorted(t["name"] for t in body["tags"]) == ["approved", "new"]


def test_another_employee_cannot_edit_someone_elses_document(
    client: TestClient, auth, employee: User, make_user, upload
) -> None:
    from app.db.models.enums import UserRole

    document = upload(auth(employee), title="Private Notes")
    intruder = make_user(UserRole.EMPLOYEE)

    response = client.patch(
        f"/api/v1/documents/{document['id']}", headers=auth(intruder), json={"title": "Hijacked Title"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_a_reviewer_may_edit_a_document_they_do_not_own(
    client: TestClient, auth, employee: User, reviewer: User, upload
) -> None:
    document = upload(auth(employee), title="Needs A Reviewer Edit")

    response = client.patch(
        f"/api/v1/documents/{document['id']}", headers=auth(reviewer), json={"title": "Edited By Reviewer"}
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Edited By Reviewer"
