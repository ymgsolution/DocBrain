"""The full loop in one test — upload → search → new version → download →
restore → review → trash → permanent delete — exercised end to end against
the real schema. The per-feature test files cover edge cases; this one
guards the *sequence*, which is where cross-feature regressions actually
show up (a version upload breaking search, a delete leaving the trash view
inconsistent, and so on)."""

import io
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.db.models import Category, User


def test_upload_search_version_download_review_and_delete(
    client: TestClient, auth, employee: User, admin: User, reviewer: User, category: Category
) -> None:
    owner = auth(employee)

    # 1. Upload
    created = client.post(
        "/api/v1/documents",
        headers=owner,
        data={"title": "Incident Response Runbook", "categoryId": str(category.id), "tags": "security,ops"},
        files={"file": ("runbook.txt", io.BytesIO(b"step one: stay calm"), "text/plain")},
    )
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    # 2. Find it by full-text search (Postgres trigger built the vector)
    found = client.get("/api/v1/documents", headers=owner, params={"q": "incident response"})
    assert document_id in [d["id"] for d in found.json()["items"]]

    # 3. Upload a second version
    v2 = client.post(
        f"/api/v1/documents/{document_id}/versions",
        headers=owner,
        data={"changeNote": "Added the escalation contacts"},
        files={"file": ("runbook-v2.txt", io.BytesIO(b"step one: stay calm, then escalate"), "text/plain")},
    )
    assert v2.status_code == 201
    assert v2.json()["versionNumber"] == 2

    # 4. Download both versions — each returns its own bytes
    assert (
        client.get(f"/api/v1/documents/{document_id}/versions/1/content", headers=owner).content
        == b"step one: stay calm"
    )
    assert (
        client.get(f"/api/v1/documents/{document_id}/versions/2/content", headers=owner).content
        == b"step one: stay calm, then escalate"
    )

    # 5. Restore v1 — a *new* v3 carrying v1's content
    restored = client.post(
        f"/api/v1/documents/{document_id}/versions/1/restore",
        headers=owner,
        json={"changeNote": "Escalation contacts were wrong, reverting"},
    )
    assert restored.status_code == 201
    assert restored.json()["versionNumber"] == 3
    assert (
        client.get(f"/api/v1/documents/{document_id}/versions/3/content", headers=owner).content
        == b"step one: stay calm"
    )

    # 6. Still searchable, and now reports three versions
    detail = client.get(f"/api/v1/documents/{document_id}", headers=owner).json()
    assert detail["versionCount"] == 3
    assert detail["currentVersion"]["versionNumber"] == 3

    # 7. Put it in the review queue, then have a reviewer clear it
    client.patch(
        f"/api/v1/documents/{document_id}",
        headers=owner,
        json={"reviewDueDate": (date.today() - timedelta(days=2)).isoformat()},
    )
    pending = client.get("/api/v1/reviews/pending", headers=auth(reviewer)).json()
    assert document_id in [i["id"] for i in pending["items"]]

    reviewed = client.post(
        f"/api/v1/documents/{document_id}/reviews", headers=auth(reviewer), json={"note": "Verified"}
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["lastReviewedAt"] is not None

    # 8. Trash it, then purge it for good
    assert client.delete(f"/api/v1/documents/{document_id}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/documents/{document_id}", headers=owner).status_code == 404

    assert (
        client.delete(f"/api/v1/documents/{document_id}/permanent", headers=auth(admin)).status_code == 204
    )
    assert document_id not in [
        d["id"] for d in client.get("/api/v1/documents/trash", headers=auth(admin)).json()["items"]
    ]
    assert document_id not in [
        d["id"] for d in client.get("/api/v1/documents", headers=owner).json()["items"]
    ]
