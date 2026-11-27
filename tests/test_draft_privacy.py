"""Drafts are private: until a club or a request is submitted, only its lead
sees it. Admins and finance approvers see it from submission on."""

import pytest

from app.models import ClubStatus, UserRole
from tests.conftest import auth, make_club, make_user
from tests.request_helpers import act_ok, create_request, funding_body


@pytest.fixture
def finance(db):
    return make_user(db, UserRole.finance_approver)


def club_ids(client, user, **params):
    response = client.get(
        "/api/clubs", params={"limit": 100, **params}, headers=auth(user)
    )
    assert response.status_code == 200, response.text
    return [club["id"] for club in response.json()["items"]]


def test_an_admin_doesnt_see_a_drafting_club(client, db, lead, admin):
    draft = make_club(db, lead, status=ClubStatus.drafting)
    submitted = make_club(db, lead, status=ClubStatus.submitted)

    assert draft.id not in club_ids(client, admin)
    assert submitted.id in club_ids(client, admin)
    assert draft.id not in club_ids(client, admin, status="drafting")
    for path in ("", "/requirements", "/events", "/comments"):
        response = client.get(f"/api/clubs/{draft.id}{path}", headers=auth(admin))
        assert response.status_code == 403, path
    # Its lead still sees it.
    assert draft.id in club_ids(client, lead)


def test_drafts_are_left_out_of_an_admins_counts_and_export(client, db, lead, admin):
    draft = make_club(db, lead, status=ClubStatus.drafting, name="Secret Draft")

    counts = client.get("/api/clubs", headers=auth(admin)).json()["status_counts"]
    export = client.get("/api/clubs/export.csv", headers=auth(admin)).text

    assert counts["drafting"] == 0
    assert "Secret Draft" not in export
    assert draft.id in club_ids(client, lead)


def test_a_draft_request_is_private_until_submitted(client, db, lead, admin, finance):
    club = make_club(db, lead, status=ClubStatus.approved)
    request = create_request(client, lead, club.id, funding_body())
    url = f"/api/requests/{request['id']}"

    for approver in (admin, finance):
        assert client.get(url, headers=auth(approver)).status_code == 403
        assert client.get(f"{url}/events", headers=auth(approver)).status_code == 403
        listed = client.get(
            "/api/requests", params={"club_id": club.id}, headers=auth(approver)
        ).json()
        assert listed["items"] == []
    assert client.get(url, headers=auth(lead)).status_code == 200

    act_ok(client, lead, request["id"], "submit")

    for approver in (admin, finance):
        assert client.get(url, headers=auth(approver)).status_code == 200
