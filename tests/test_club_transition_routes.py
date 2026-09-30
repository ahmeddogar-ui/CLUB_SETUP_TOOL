"""Tickets 17-21: submit, start-review, request-changes, reject, approve, resubmit."""

import pytest

from app.models import ClubEvent, ClubStatus, RequirementStatus
from tests.conftest import (
    approve_all_requirements,
    auth,
    create_club,
    provide_all_documents,
    requirements_for,
)


def event_count(db, club_id) -> int:
    return db.query(ClubEvent).filter(ClubEvent.club_id == club_id).count()


def post(client, club_id, action, user, **kwargs):
    return client.post(f"/clubs/{club_id}/{action}", headers=auth(user), **kwargs)


@pytest.fixture
def draft(client, lead):
    return create_club(client, lead)


@pytest.fixture
def submitted(client, db, draft, lead):
    provide_all_documents(db, draft["id"])
    response = post(client, draft["id"], "submit", lead)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def under_review(client, submitted, admin):
    response = post(client, submitted["id"], "start-review", admin)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def changes_requested(client, under_review, admin):
    response = post(
        client, under_review["id"], "request-changes", admin, json={"note": "fix budget"}
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- submit (ticket 17) ----------------------------------------------------


def test_submit_complete_draft(client, db, draft, lead):
    provide_all_documents(db, draft["id"])
    response = post(client, draft["id"], "submit", lead)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert event_count(db, draft["id"]) == 2  # created + submitted


def test_submit_incomplete_draft_names_missing_items(client, db, draft, lead):
    response = post(client, draft["id"], "submit", lead)
    assert response.status_code == 409
    detail = response.json()["detail"]
    for missing in ("constitution", "exec_list", "budget", "advisor_form"):
        assert missing in detail
    assert "bank_account_setup" not in detail  # checklist items aren't required yet
    assert event_count(db, draft["id"]) == 1


def test_submit_twice_conflicts(client, submitted, lead):
    response = post(client, submitted["id"], "submit", lead)
    assert response.status_code == 409


def test_submit_someone_elses_club_is_403_before_transition_logic(
    client, submitted, other_lead
):
    # This would be a 409 if transition logic ran first; 403 proves ownership is checked first.
    response = post(client, submitted["id"], "submit", other_lead)
    assert response.status_code == 403


def test_submit_missing_club_404(client, lead):
    assert post(client, 999999, "submit", lead).status_code == 404


def test_submit_requires_auth(client, draft):
    assert client.post(f"/clubs/{draft['id']}/submit").status_code == 401


# --- start-review (ticket 20) ----------------------------------------------


def test_start_review_moves_submitted_and_records_one_event(client, db, submitted, admin):
    before = event_count(db, submitted["id"])
    response = post(client, submitted["id"], "start-review", admin)
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"
    assert event_count(db, submitted["id"]) == before + 1


def test_start_review_on_draft_conflicts(client, draft, admin):
    assert post(client, draft["id"], "start-review", admin).status_code == 409


def test_start_review_on_under_review_conflicts(client, under_review, admin):
    assert post(client, under_review["id"], "start-review", admin).status_code == 409


def test_start_review_rejects_club_lead_on_role(client, submitted, lead):
    assert post(client, submitted["id"], "start-review", lead).status_code == 403


def test_start_review_missing_club_404(client, admin):
    assert post(client, 999999, "start-review", admin).status_code == 404


# --- request-changes & reject (ticket 19) ----------------------------------


@pytest.mark.parametrize("action", ["request-changes", "reject"])
@pytest.mark.parametrize("body", [None, {}, {"note": ""}, {"note": "   "}])
def test_note_required(client, db, under_review, admin, action, body):
    response = post(client, under_review["id"], action, admin, json=body)
    assert response.status_code == 422
    assert event_count(db, under_review["id"]) == 3


@pytest.mark.parametrize(
    ("action", "expected"), [("request-changes", "changes_requested"), ("reject", "rejected")]
)
def test_note_actions_store_note_on_event(client, db, under_review, admin, action, expected):
    response = post(client, under_review["id"], action, admin, json={"note": " Needs work "})
    assert response.status_code == 200
    assert response.json()["status"] == expected
    event = (
        db.query(ClubEvent)
        .filter(ClubEvent.club_id == under_review["id"])
        .order_by(ClubEvent.id.desc())
        .first()
    )
    assert event.to_status == ClubStatus(expected)
    assert event.note == "Needs work"


@pytest.mark.parametrize("action", ["request-changes", "reject"])
def test_note_actions_reject_club_lead(client, under_review, lead, action):
    response = post(client, under_review["id"], action, lead, json={"note": "x"})
    assert response.status_code == 403


@pytest.mark.parametrize("action", ["request-changes", "reject"])
def test_note_actions_require_under_review(client, submitted, admin, action):
    response = post(client, submitted["id"], action, admin, json={"note": "x"})
    assert response.status_code == 409


# --- approve (ticket 21) ---------------------------------------------------


def test_approve_when_every_requirement_approved(client, db, under_review, admin):
    approve_all_requirements(db, under_review["id"])
    response = post(client, under_review["id"], "approve", admin)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_approve_blocked_names_outstanding_requirements(client, db, under_review, admin):
    approve_all_requirements(db, under_review["id"])
    requirements = requirements_for(db, under_review["id"])
    requirements["budget"].status = RequirementStatus.rejected
    requirements["exec_onboarding"].status = RequirementStatus.pending
    db.commit()

    response = post(client, under_review["id"], "approve", admin)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "budget" in detail and "exec_onboarding" in detail
    assert "constitution" not in detail


def test_approve_rejects_club_lead(client, db, under_review, lead):
    approve_all_requirements(db, under_review["id"])
    assert post(client, under_review["id"], "approve", lead).status_code == 403


# --- resubmit (ticket 21) --------------------------------------------------


def test_resubmit_moves_back_to_submitted(client, changes_requested, lead):
    response = post(client, changes_requested["id"], "resubmit", lead)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"


def test_second_full_loop_accumulates_events(client, db, changes_requested, lead, admin):
    club_id = changes_requested["id"]
    assert post(client, club_id, "resubmit", lead).status_code == 200
    assert post(client, club_id, "start-review", admin).status_code == 200
    assert (
        post(client, club_id, "request-changes", admin, json={"note": "round 2"}).status_code
        == 200
    )
    assert post(client, club_id, "resubmit", lead).status_code == 200

    events = (
        db.query(ClubEvent).filter(ClubEvent.club_id == club_id).order_by(ClubEvent.id).all()
    )
    assert [e.event_type for e in events] == [
        "created",
        "submitted",
        "review_started",
        "changes_requested",
        "resubmitted",
        "review_started",
        "changes_requested",
        "resubmitted",
    ]
    assert [e.note for e in events if e.event_type == "changes_requested"] == [
        "fix budget",
        "round 2",
    ]


def test_resubmit_someone_elses_club_is_403(client, changes_requested, other_lead):
    assert post(client, changes_requested["id"], "resubmit", other_lead).status_code == 403


def test_resubmit_ownership_checked_before_status(client, draft, other_lead):
    # A drafting club would be a 409 for its owner; a stranger must get 403 instead.
    assert post(client, draft["id"], "resubmit", other_lead).status_code == 403


def test_resubmit_only_from_changes_requested(client, draft, lead):
    assert post(client, draft["id"], "resubmit", lead).status_code == 409


def test_resubmit_still_runs_submit_guard(client, db, changes_requested, lead):
    requirements_for(db, changes_requested["id"])["budget"].status = RequirementStatus.rejected
    db.commit()
    response = post(client, changes_requested["id"], "resubmit", lead)
    assert response.status_code == 409
    assert "budget" in response.json()["detail"]
