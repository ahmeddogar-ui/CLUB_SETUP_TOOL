"""The whole submit -> review -> approve flow, driven only through the HTTP API.

The only thing done outside the API is creating the admin user, because there is no
admin-registration route yet.
"""

from app.models import ClubEvent, UserRole
from tests.conftest import auth, make_user

DOCUMENTS = ("constitution", "exec_list", "budget", "advisor_form")
CHECKLIST = ("bank_account_setup", "exec_onboarding")


def register_and_login(client, email):
    response = client.post(
        "/auth/register", json={"name": "Lead", "email": email, "password": "pw123456"}
    )
    assert response.status_code == 201, response.text
    response = client.post("/auth/login", data={"username": email, "password": "pw123456"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ok(response, expected_status=200):
    assert response.status_code == expected_status, response.text
    return response.json()


def test_full_flow_to_approval(client, db):
    lead = register_and_login(client, "e2e-lead@example.com")
    admin = auth(make_user(db, UserRole.admin))

    club = ok(
        client.post("/clubs", json={"name": "Robotics", "description": "Build robots"}, headers=lead),
        201,
    )
    club_id = club["id"]

    # Submitting before any documents are attached is blocked.
    assert client.post(f"/clubs/{club_id}/submit", headers=lead).status_code == 409

    for requirement_type in DOCUMENTS:
        ok(
            client.put(
                f"/clubs/{club_id}/requirements/{requirement_type}/link",
                json={"link_url": f"https://drive.example.com/{requirement_type}"},
                headers=lead,
            )
        )

    assert ok(client.post(f"/clubs/{club_id}/submit", headers=lead))["status"] == "submitted"
    assert ok(client.post(f"/clubs/{club_id}/start-review", headers=admin))["status"] == "under_review"

    # Approve is blocked until every requirement has been individually approved.
    blocked = client.post(f"/clubs/{club_id}/approve", headers=admin)
    assert blocked.status_code == 409
    for requirement_type in DOCUMENTS + CHECKLIST:
        assert requirement_type in blocked.json()["detail"]

    for requirement_type in DOCUMENTS + CHECKLIST:
        body = ok(
            client.post(
                f"/clubs/{club_id}/requirements/{requirement_type}/approve", headers=admin
            )
        )
        assert body["status"] == "approved"

    assert ok(client.post(f"/clubs/{club_id}/approve", headers=admin))["status"] == "approved"
    assert ok(client.get(f"/clubs/{club_id}", headers=lead))["status"] == "approved"

    events = db.query(ClubEvent).filter(ClubEvent.club_id == club_id).order_by(ClubEvent.id).all()
    assert [e.event_type for e in events] == (
        ["created"]
        + ["requirement_submitted"] * 4
        + ["submitted", "review_started"]
        + ["requirement_approved"] * 6
        + ["approved"]
    )


def test_full_flow_with_rejected_document_and_changes_loop(client, db):
    lead = register_and_login(client, "e2e-loop@example.com")
    admin = auth(make_user(db, UserRole.admin))

    club_id = ok(
        client.post("/clubs", json={"name": "Film", "description": "Watch films"}, headers=lead),
        201,
    )["id"]
    for requirement_type in DOCUMENTS:
        ok(
            client.put(
                f"/clubs/{club_id}/requirements/{requirement_type}/link",
                json={"link_url": f"https://drive.example.com/{requirement_type}"},
                headers=lead,
            )
        )
    ok(client.post(f"/clubs/{club_id}/submit", headers=lead))
    ok(client.post(f"/clubs/{club_id}/start-review", headers=admin))

    # Round 1: budget is rejected, everything else approved, changes requested.
    for requirement_type in ("constitution", "exec_list", "advisor_form") + CHECKLIST:
        ok(client.post(f"/clubs/{club_id}/requirements/{requirement_type}/approve", headers=admin))
    ok(
        client.post(
            f"/clubs/{club_id}/requirements/budget/reject",
            json={"note": "Totals don't add up"},
            headers=admin,
        )
    )
    ok(
        client.post(
            f"/clubs/{club_id}/request-changes", json={"note": "Fix the budget"}, headers=admin
        )
    )

    # Resubmitting without replacing the rejected budget is blocked and says why.
    blocked = client.post(f"/clubs/{club_id}/resubmit", headers=lead)
    assert blocked.status_code == 409
    assert "budget" in blocked.json()["detail"]

    ok(
        client.put(
            f"/clubs/{club_id}/requirements/budget/link",
            json={"link_url": "https://drive.example.com/budget-v2"},
            headers=lead,
        )
    )
    assert ok(client.post(f"/clubs/{club_id}/resubmit", headers=lead))["status"] == "submitted"

    # Round 2: only the new budget needs approving; earlier approvals carry over.
    ok(client.post(f"/clubs/{club_id}/start-review", headers=admin))
    ok(client.post(f"/clubs/{club_id}/requirements/budget/approve", headers=admin))
    assert ok(client.post(f"/clubs/{club_id}/approve", headers=admin))["status"] == "approved"

    events = db.query(ClubEvent).filter(ClubEvent.club_id == club_id).order_by(ClubEvent.id).all()

    club_level = [e for e in events if e.requirement_id is None]
    assert [e.event_type for e in club_level] == [
        "created",
        "submitted",
        "review_started",
        "changes_requested",
        "resubmitted",
        "review_started",
        "approved",
    ]
    assert club_level[3].note == "Fix the budget"

    # The budget's own story survives in history even though the requirement row
    # itself now only holds the final approved link.
    budget_id = next(e.requirement_id for e in events if e.event_type == "requirement_rejected")
    budget = [
        (e.event_type, e.link_url, e.note) for e in events if e.requirement_id == budget_id
    ]
    assert budget == [
        ("requirement_submitted", "https://drive.example.com/budget", None),
        ("requirement_rejected", None, "Totals don't add up"),
        ("requirement_submitted", "https://drive.example.com/budget-v2", None),
        ("requirement_approved", None, None),
    ]
