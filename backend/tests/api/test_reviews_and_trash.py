"""Review reminders and the two-stage delete (Trash, then permanent) — the
two flows with real role gates on them."""

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient

from app.db.models import Category, User


def test_a_reviewer_can_mark_a_document_reviewed(
    client: TestClient, auth, employee: User, reviewer: User, upload
) -> None:
    document = upload(auth(employee), title="Policy Awaiting Review")

    response = client.post(
        f"/api/v1/documents/{document['id']}/reviews",
        headers=auth(reviewer),
        json={"note": "Checked and still accurate"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["lastReviewedAt"] is not None


def test_an_employee_cannot_mark_a_document_reviewed(
    client: TestClient, auth, employee: User, upload
) -> None:
    document = upload(auth(employee), title="Policy Awaiting Review")

    response = client.post(
        f"/api/v1/documents/{document['id']}/reviews", headers=auth(employee), json={"note": "Looks fine"}
    )

    assert response.status_code == 403


def test_marking_reviewed_pushes_the_due_date_out_by_the_category_period(
    client: TestClient, auth, employee: User, reviewer: User, db_session, category: Category, upload, today
) -> None:
    category.default_review_period_days = 90
    db_session.flush()
    document = upload(auth(employee), title="Annually Reviewed Policy")

    response = client.post(
        f"/api/v1/documents/{document['id']}/reviews", headers=auth(reviewer), json={"note": None}
    )

    assert response.status_code == 200
    expected = (today + timedelta(days=90)).isoformat()
    assert response.json()["reviewDueDate"] == expected


def test_pending_reviews_is_closed_to_employees(client: TestClient, auth, employee: User) -> None:
    assert client.get("/api/v1/reviews/pending", headers=auth(employee)).status_code == 403


def test_pending_reviews_lists_a_document_that_is_due(
    client: TestClient, auth, employee: User, reviewer: User, upload, today
) -> None:
    document = upload(auth(employee), title="Due Very Soon")
    client.patch(
        f"/api/v1/documents/{document['id']}",
        headers=auth(employee),
        json={"reviewDueDate": (today + timedelta(days=3)).isoformat()},
    )

    response = client.get("/api/v1/reviews/pending", headers=auth(reviewer))

    assert response.status_code == 200
    assert document["id"] in [item["id"] for item in response.json()["items"]]


def test_an_overdue_document_is_reported_as_overdue(
    client: TestClient, auth, employee: User, reviewer: User, upload, today
) -> None:
    document = upload(auth(employee), title="Long Overdue")
    client.patch(
        f"/api/v1/documents/{document['id']}",
        headers=auth(employee),
        json={"reviewDueDate": (today - timedelta(days=10)).isoformat()},
    )

    items = client.get("/api/v1/reviews/pending", headers=auth(reviewer)).json()["items"]
    entry = next(i for i in items if i["id"] == document["id"])

    assert entry["reviewStatus"] == "overdue"
    assert entry["daysOverdue"] == 10


def test_soft_delete_moves_a_document_to_trash(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    document = upload(headers, title="Document To Bin")

    assert client.delete(f"/api/v1/documents/{document['id']}", headers=headers).status_code == 204

    # Gone from the normal view...
    assert client.get(f"/api/v1/documents/{document['id']}", headers=headers).status_code == 404
    # ...but recoverable from Trash.
    trash_ids = [d["id"] for d in client.get("/api/v1/documents/trash", headers=headers).json()["items"]]
    assert document["id"] in trash_ids


def test_restoring_from_trash_brings_a_document_back(client: TestClient, auth, employee: User, upload) -> None:
    headers = auth(employee)
    document = upload(headers, title="Deleted By Mistake")
    client.delete(f"/api/v1/documents/{document['id']}", headers=headers)

    response = client.post(f"/api/v1/documents/{document['id']}/restore", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert client.get(f"/api/v1/documents/{document['id']}", headers=headers).status_code == 200


def test_permanent_delete_requires_an_admin(
    client: TestClient, auth, employee: User, reviewer: User, upload
) -> None:
    headers = auth(employee)
    document = upload(headers, title="Not Yours To Purge")
    client.delete(f"/api/v1/documents/{document['id']}", headers=headers)

    assert client.delete(f"/api/v1/documents/{document['id']}/permanent", headers=headers).status_code == 403
    assert (
        client.delete(f"/api/v1/documents/{document['id']}/permanent", headers=auth(reviewer)).status_code
        == 403
    )


def test_permanent_delete_only_works_on_a_trashed_document(
    client: TestClient, auth, employee: User, admin: User, upload
) -> None:
    document = upload(auth(employee), title="Still Active")

    response = client.delete(f"/api/v1/documents/{document['id']}/permanent", headers=auth(admin))

    assert response.status_code == 422


def test_an_admin_can_permanently_delete_a_trashed_document(
    client: TestClient, auth, employee: User, admin: User, upload
) -> None:
    document = upload(auth(employee), title="Purge Me")
    client.delete(f"/api/v1/documents/{document['id']}", headers=auth(employee))

    response = client.delete(f"/api/v1/documents/{document['id']}/permanent", headers=auth(admin))

    assert response.status_code == 204
    assert client.get(f"/api/v1/documents/{document['id']}", headers=auth(admin)).status_code == 404
    trash_ids = [d["id"] for d in client.get("/api/v1/documents/trash", headers=auth(admin)).json()["items"]]
    assert document["id"] not in trash_ids


def test_restoring_a_document_that_is_not_in_trash_is_rejected(
    client: TestClient, auth, employee: User, upload
) -> None:
    document = upload(auth(employee), title="Never Deleted")

    response = client.post(f"/api/v1/documents/{document['id']}/restore", headers=auth(employee))

    assert response.status_code == 422


def test_trash_is_scoped_to_what_you_deleted_yourself(
    client: TestClient, auth, employee: User, make_user, upload
) -> None:
    from app.db.models.enums import UserRole

    document = upload(auth(employee), title="My Own Deletion")
    client.delete(f"/api/v1/documents/{document['id']}", headers=auth(employee))

    other = make_user(UserRole.EMPLOYEE)
    other_trash = client.get("/api/v1/documents/trash", headers=auth(other)).json()

    assert document["id"] not in [d["id"] for d in other_trash["items"]]


def test_unknown_document_ids_are_404_not_500(client: TestClient, auth, admin: User) -> None:
    missing = uuid.uuid4()
    assert client.delete(f"/api/v1/documents/{missing}", headers=auth(admin)).status_code == 404
    assert client.post(f"/api/v1/documents/{missing}/restore", headers=auth(admin)).status_code == 404
