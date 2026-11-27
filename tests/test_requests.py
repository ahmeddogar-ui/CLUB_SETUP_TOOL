"""The request engine: one state machine and approval chain for every type."""

import pytest
from sqlalchemy import select

from app.models import ClubStatus, Event, RequestApproval, UserRole
from tests.conftest import auth, make_club, make_user
from tests.request_helpers import (
    a_room,
    act,
    act_ok,
    at,
    booking_body,
    create_request,
    funding_body,
)


@pytest.fixture
def finance(db):
    return make_user(db, UserRole.finance_approver)


@pytest.fixture
def club(db, lead):
    return make_club(db, lead, status=ClubStatus.approved)


@pytest.fixture
def funding(client, lead, club):
    return create_request(client, lead, club.id, funding_body())


def test_a_funding_request_starts_as_a_draft_with_a_total(funding, club):
    assert funding["status"] == "draft"
    assert funding["club_id"] == club.id
    assert funding["round"] == 0
    assert funding["awaiting_role"] is None
    assert funding["approval_steps"] == ["admin", "finance_approver"]
    assert funding["details"]["total_cents"] == 17550
    assert funding["allowed_actions"] == ["submit", "cancel"]


def test_funding_needs_the_admin_then_finance(
    client, db, lead, admin, finance, funding
):
    request_id = funding["id"]
    submitted = act_ok(client, lead, request_id, "submit")
    assert submitted["status"] == "submitted"
    assert submitted["awaiting_role"] == "admin"

    act_ok(client, admin, request_id, "start-review")
    after_admin = act_ok(client, admin, request_id, "approve", note="Fine by me")
    assert after_admin["status"] == "in_review"
    assert after_admin["awaiting_role"] == "finance_approver"
    [approval] = after_admin["approvals"]
    assert approval["step"] == 0
    assert approval["role"] == "admin"
    assert approval["approver_name"] == admin.name
    assert approval["note"] == "Fine by me"

    approved = act_ok(client, finance, request_id, "approve")
    assert approved["status"] == "approved"
    assert approved["awaiting_role"] is None
    assert [step["role"] for step in approved["approvals"]] == [
        "admin",
        "finance_approver",
    ]


def test_each_step_belongs_to_its_role(client, lead, admin, finance, funding):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    # Finance can't start the admin's review, nor approve the admin's step.
    assert act(client, finance, request_id, "start-review").status_code == 403
    act_ok(client, admin, request_id, "start-review")
    assert act(client, finance, request_id, "approve").status_code == 403
    act_ok(client, admin, request_id, "approve")
    # And the admin can't approve the finance step.
    assert act(client, admin, request_id, "approve").status_code == 403


def test_actions_out_of_order_are_409(client, lead, admin, funding):
    request_id = funding["id"]
    assert act(client, admin, request_id, "approve").status_code == 409
    act_ok(client, lead, request_id, "submit")
    assert act(client, lead, request_id, "submit").status_code == 409
    assert act(client, admin, request_id, "approve").status_code == 409


@pytest.mark.parametrize("action", ["reject", "request-changes"])
def test_reject_and_request_changes_need_a_note(client, lead, admin, funding, action):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    act_ok(client, admin, request_id, "start-review")
    assert act(client, admin, request_id, action).status_code == 422
    assert act(client, admin, request_id, action, note="   ").status_code == 422


def test_resubmitting_after_changes_starts_a_new_round(
    client, lead, admin, finance, funding
):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    act_ok(client, admin, request_id, "start-review")
    act_ok(client, admin, request_id, "approve")
    changes = act_ok(
        client, finance, request_id, "request-changes", note="Split the venue cost"
    )
    assert changes["status"] == "changes_requested"
    assert changes["awaiting_role"] is None

    edited = client.patch(
        f"/api/requests/{request_id}",
        json={"details": funding_body(items=[("Venue", 4000)])["details"]},
        headers=auth(lead),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["details"]["total_cents"] == 4000

    resubmitted = act_ok(client, lead, request_id, "submit")
    assert resubmitted["round"] == 2
    assert resubmitted["awaiting_role"] == "admin"
    # The earlier round's admin approval doesn't carry over.
    assert resubmitted["approvals"] == []


def test_rejected_and_cancelled_are_final(client, lead, admin, funding, club):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    act_ok(client, admin, request_id, "start-review")
    act_ok(client, admin, request_id, "reject", note="Out of budget")
    assert act(client, lead, request_id, "submit").status_code == 409
    assert act(client, lead, request_id, "cancel").status_code == 409

    other = create_request(client, lead, club.id, funding_body())
    act_ok(client, lead, other["id"], "cancel")
    assert act(client, lead, other["id"], "submit").status_code == 409


def test_approved_funding_cant_be_cancelled(client, lead, admin, finance, funding):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    act_ok(client, admin, request_id, "start-review")
    act_ok(client, admin, request_id, "approve")
    approved = act_ok(client, finance, request_id, "approve")
    assert approved["allowed_actions"] == []

    response = act(client, lead, request_id, "cancel")

    assert response.status_code == 409
    assert "approved funding" in response.json()["detail"].lower()


def test_can_edit_follows_the_rule(client, lead, admin, funding):
    url = f"/api/requests/{funding['id']}"
    assert client.get(url, headers=auth(lead)).json()["can_edit"] is True
    assert client.get(url, headers=auth(admin)).json()["can_edit"] is False
    act_ok(client, lead, funding["id"], "submit")
    assert client.get(url, headers=auth(lead)).json()["can_edit"] is False


def test_the_lead_can_cancel_an_approved_booking_before_it_starts(
    client, lead, admin, db, club
):
    booking = create_request(
        client, lead, club.id, booking_body(a_room(db).id, at(10), at(11))
    )
    act_ok(client, lead, booking["id"], "submit")
    act_ok(client, admin, booking["id"], "start-review")
    assert act_ok(client, admin, booking["id"], "approve")["status"] == "approved"

    assert act_ok(client, lead, booking["id"], "cancel")["status"] == "cancelled"


def test_only_the_club_lead_creates_and_edits(
    client, db, other_lead, admin, club, funding
):
    response = client.post(
        f"/api/clubs/{club.id}/requests", json=funding_body(), headers=auth(other_lead)
    )
    assert response.status_code == 403
    assert (
        client.post(
            f"/api/clubs/{club.id}/requests", json=funding_body(), headers=auth(admin)
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/requests/{funding['id']}",
            json={"title": "Mine now"},
            headers=auth(other_lead),
        ).status_code
        == 403
    )


def test_requests_need_an_approved_club(client, db, lead):
    drafting = make_club(db, lead, status=ClubStatus.drafting)
    response = client.post(
        f"/api/clubs/{drafting.id}/requests", json=funding_body(), headers=auth(lead)
    )
    assert response.status_code == 409
    assert "approved" in response.json()["detail"]


def test_editing_after_submission_is_409(client, lead, funding):
    act_ok(client, lead, funding["id"], "submit")
    response = client.patch(
        f"/api/requests/{funding['id']}", json={"title": "New"}, headers=auth(lead)
    )
    assert response.status_code == 409


def test_a_request_keeps_its_type(client, db, lead, funding):
    body = booking_body(a_room(db).id, at(10), at(11))
    response = client.patch(
        f"/api/requests/{funding['id']}",
        json={"details": body["details"]},
        headers=auth(lead),
    )
    assert response.status_code == 409


def test_who_can_see_a_request(
    client, db, lead, other_lead, admin, finance, club, funding
):
    booking = create_request(
        client, lead, club.id, booking_body(a_room(db).id, at(10), at(11))
    )
    url = f"/api/requests/{funding['id']}"
    assert client.get(url, headers=auth(lead)).status_code == 200
    assert client.get(url, headers=auth(admin)).status_code == 200
    assert client.get(url, headers=auth(finance)).status_code == 200
    assert client.get(url, headers=auth(other_lead)).status_code == 403
    # Finance approvers only see the types they approve.
    assert (
        client.get(f"/api/requests/{booking['id']}", headers=auth(finance)).status_code
        == 403
    )
    assert client.get("/api/requests/999999", headers=auth(admin)).status_code == 404


def test_allowed_actions_follow_the_viewer(client, lead, admin, finance, funding):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    as_admin = client.get(f"/api/requests/{request_id}", headers=auth(admin)).json()
    as_finance = client.get(f"/api/requests/{request_id}", headers=auth(finance)).json()
    as_lead = client.get(f"/api/requests/{request_id}", headers=auth(lead)).json()
    assert as_admin["allowed_actions"] == ["start_review"]
    assert as_finance["allowed_actions"] == []
    assert as_lead["allowed_actions"] == ["cancel"]


def test_every_action_writes_one_event(client, db, lead, admin, finance, funding, club):
    request_id = funding["id"]
    act_ok(client, lead, request_id, "submit")
    act_ok(client, admin, request_id, "start-review")
    act_ok(client, admin, request_id, "approve")
    act_ok(client, finance, request_id, "approve")

    events = db.scalars(
        select(Event).where(Event.request_id == request_id).order_by(Event.id)
    ).all()
    assert [event.event_type for event in events] == [
        "request_created",
        "request_submitted",
        "request_review_started",
        "request_step_approved",
        "request_approved",
    ]
    assert {event.club_id for event in events} == {club.id}
    history = client.get(
        f"/api/requests/{request_id}/events", headers=auth(lead)
    ).json()
    assert history[0]["event_type"] == "request_approved"
    assert history[0]["actor_name"] == finance.name
    # Request events stay out of the club's registration history.
    club_history = client.get(f"/api/clubs/{club.id}/events", headers=auth(lead)).json()
    assert all(not event["event_type"].startswith("request_") for event in club_history)


def test_one_approval_per_step_per_round(db, client, lead, admin, funding):
    act_ok(client, lead, funding["id"], "submit")
    act_ok(client, admin, funding["id"], "start-review")
    act_ok(client, admin, funding["id"], "approve")
    approvals = db.scalars(
        select(RequestApproval).where(RequestApproval.request_id == funding["id"])
    ).all()
    assert [(approval.round, approval.step) for approval in approvals] == [(1, 0)]


@pytest.mark.parametrize(
    "items",
    [[], [("Pizza", 0)], [("Pizza", -5)], [("", 100)], [("Pizza", 100_000_001)]],
)
def test_invalid_line_items_are_422(client, lead, club, items):
    response = client.post(
        f"/api/clubs/{club.id}/requests",
        json=funding_body(items=items),
        headers=auth(lead),
    )
    assert response.status_code == 422


def test_listing_requests(client, db, lead, other_lead, admin, finance, club, funding):
    booking = create_request(
        client, lead, club.id, booking_body(a_room(db).id, at(10), at(12))
    )
    act_ok(client, lead, funding["id"], "submit")

    def ids(user, **params):
        response = client.get("/api/requests", params=params, headers=auth(user))
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    assert ids(lead, club_id=club.id, sort="newest") == [funding["id"], booking["id"]]
    assert ids(other_lead) == []
    assert ids(finance, club_id=club.id) == [funding["id"]]
    assert ids(admin, awaiting_me="true", club_id=club.id) == [funding["id"]]
    assert ids(finance, awaiting_me="true", club_id=club.id) == []
    assert ids(admin, club_id=club.id, status="draft") == [booking["id"]]

    page = client.get(
        "/api/requests", params={"club_id": club.id}, headers=auth(lead)
    ).json()
    by_id = {item["id"]: item for item in page["items"]}
    assert by_id[funding["id"]]["total_cents"] == 17550
    assert by_id[funding["id"]]["club_name"] == club.name
    assert by_id[booking["id"]]["room_name"] == a_room(db).name
    assert by_id[booking["id"]]["total_cents"] is None
