"""Read-only JSON endpoints the frontend needs: a club's requirements and history."""

import pytest

from tests.conftest import auth, create_club, provide_all_documents

READ_PATHS = ("requirements", "events")


@pytest.fixture
def club(client, lead):
    return create_club(client, lead)


def test_requirements_lists_all_six_in_creation_order(client, club, lead):
    response = client.get(f"/clubs/{club['id']}/requirements", headers=auth(lead))

    assert response.status_code == 200
    body = response.json()
    assert [row["requirement_type"] for row in body] == [
        "constitution",
        "exec_list",
        "budget",
        "advisor_form",
        "bank_account_setup",
        "exec_onboarding",
    ]
    assert all(row["status"] == "pending" for row in body)
    assert all(row["club_id"] == club["id"] for row in body)


def test_events_newest_first_with_actor_name(client, db, club, lead):
    provide_all_documents(db, club["id"])
    assert client.post(f"/clubs/{club['id']}/submit", headers=auth(lead)).status_code == 200

    response = client.get(f"/clubs/{club['id']}/events", headers=auth(lead))

    assert response.status_code == 200
    events = response.json()
    assert [event["event_type"] for event in events] == ["submitted", "created"]
    assert events[0]["from_status"] == "drafting"
    assert events[0]["to_status"] == "submitted"
    assert events[1]["from_status"] is None
    assert all(event["actor_name"] == lead.name for event in events)
    assert all(event["created_at"] for event in events)


def test_events_include_requirement_link_and_id(client, club, lead):
    client.put(
        f"/clubs/{club['id']}/requirements/budget/link",
        json={"link_url": "https://docs.example.com/budget"},
        headers=auth(lead),
    )
    requirements = client.get(
        f"/clubs/{club['id']}/requirements", headers=auth(lead)
    ).json()
    budget_id = next(r["id"] for r in requirements if r["requirement_type"] == "budget")

    latest = client.get(f"/clubs/{club['id']}/events", headers=auth(lead)).json()[0]

    assert latest["event_type"] == "requirement_submitted"
    assert latest["requirement_id"] == budget_id
    assert latest["link_url"] == "https://docs.example.com/budget"


@pytest.mark.parametrize("path", READ_PATHS)
def test_admin_can_read_any_club(client, club, admin, path):
    assert client.get(f"/clubs/{club['id']}/{path}", headers=auth(admin)).status_code == 200


@pytest.mark.parametrize("path", READ_PATHS)
def test_other_lead_is_forbidden(client, club, other_lead, path):
    response = client.get(f"/clubs/{club['id']}/{path}", headers=auth(other_lead))
    assert response.status_code == 403


@pytest.mark.parametrize("path", READ_PATHS)
def test_missing_club_is_404(client, lead, path):
    assert client.get(f"/clubs/999999/{path}", headers=auth(lead)).status_code == 404


@pytest.mark.parametrize("path", READ_PATHS)
def test_requires_authentication(client, club, path):
    assert client.get(f"/clubs/{club['id']}/{path}").status_code == 401
