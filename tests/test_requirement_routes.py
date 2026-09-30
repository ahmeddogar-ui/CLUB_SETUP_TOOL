"""Ticket 22: set a requirement's link, approve it, reject it."""

import pytest

from app.models import ClubEvent, ClubStatus, RequirementStatus
from tests.conftest import auth, create_club, provide_all_documents, requirements_for

DOCUMENTS = ("constitution", "exec_list", "budget", "advisor_form")
CHECKLIST = ("bank_account_setup", "exec_onboarding")


def set_link(client, club_id, requirement_type, user, link="https://docs.example.com/file"):
    return client.put(
        f"/clubs/{club_id}/requirements/{requirement_type}/link",
        json={"link_url": link},
        headers=auth(user),
    )


def review(client, club_id, requirement_type, action, user, **kwargs):
    return client.post(
        f"/clubs/{club_id}/requirements/{requirement_type}/{action}",
        headers=auth(user),
        **kwargs,
    )


@pytest.fixture
def draft(client, lead):
    return create_club(client, lead)


@pytest.fixture
def under_review(client, db, draft, lead, admin):
    provide_all_documents(db, draft["id"])
    assert client.post(f"/clubs/{draft['id']}/submit", headers=auth(lead)).status_code == 200
    assert (
        client.post(f"/clubs/{draft['id']}/start-review", headers=auth(admin)).status_code
        == 200
    )
    return draft


# --- set link --------------------------------------------------------------


@pytest.mark.parametrize("requirement_type", DOCUMENTS)
def test_set_link_on_document_marks_it_provided(client, db, draft, lead, requirement_type):
    response = set_link(client, draft["id"], requirement_type, lead)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["link_url"] == "https://docs.example.com/file"

    db.expire_all()
    row = requirements_for(db, draft["id"])[requirement_type]
    assert row.status == RequirementStatus.submitted
    assert row.link_url == "https://docs.example.com/file"


@pytest.mark.parametrize("requirement_type", CHECKLIST)
def test_set_link_on_checklist_rejected(client, db, draft, lead, requirement_type):
    response = set_link(client, draft["id"], requirement_type, lead)
    assert response.status_code == 409
    assert "checklist" in response.json()["detail"]
    row = requirements_for(db, draft["id"])[requirement_type]
    assert row.link_url is None
    assert row.status == RequirementStatus.pending


def test_set_link_someone_elses_club_is_403(client, draft, other_lead):
    assert set_link(client, draft["id"], "budget", other_lead).status_code == 403


def test_set_link_missing_club_404(client, lead):
    assert set_link(client, 999999, "budget", lead).status_code == 404


def test_set_link_unknown_requirement_type_422(client, draft, lead):
    assert set_link(client, draft["id"], "not_a_type", lead).status_code == 422


def test_set_link_missing_requirement_row_404(client, db, draft, lead):
    db.delete(requirements_for(db, draft["id"])["budget"])
    db.commit()
    assert set_link(client, draft["id"], "budget", lead).status_code == 404


@pytest.mark.parametrize("link", ["not a url", "", "ftp://example.com/x"])
def test_set_link_invalid_url_422(client, draft, lead, link):
    assert set_link(client, draft["id"], "budget", lead, link).status_code == 422


def test_set_link_blocked_once_submitted(client, under_review, lead):
    assert set_link(client, under_review["id"], "budget", lead).status_code == 409


def test_set_link_does_not_touch_other_clubs(client, db, draft, lead):
    other = create_club(client, lead, name="Other Club")
    set_link(client, draft["id"], "budget", lead)
    assert requirements_for(db, other["id"])["budget"].status == RequirementStatus.pending


# --- approve / reject ------------------------------------------------------


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_club_lead_cannot_review_own_requirement(client, db, under_review, lead, action):
    response = review(client, under_review["id"], "budget", action, lead, json={"note": "x"})
    assert response.status_code == 403
    assert requirements_for(db, under_review["id"])["budget"].status == RequirementStatus.submitted


@pytest.mark.parametrize("requirement_type", DOCUMENTS + CHECKLIST)
def test_admin_approves_requirement(client, db, under_review, admin, requirement_type):
    response = review(client, under_review["id"], requirement_type, "approve", admin)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_approve_with_optional_note(client, db, under_review, admin):
    response = review(
        client, under_review["id"], "budget", "approve", admin, json={"note": "Looks good"}
    )
    assert response.status_code == 200
    assert response.json()["reviewer_note"] == "Looks good"


def test_approve_wrong_club_requirement_pairing_fails_cleanly(
    client, db, under_review, lead, admin
):
    # Club B has its own budget row; club A's has been removed. Approving club A's
    # budget must 404 rather than silently hitting club B's row.
    other = create_club(client, lead, name="Other Club")
    db.delete(requirements_for(db, under_review["id"])["budget"])
    db.commit()

    response = review(client, under_review["id"], "budget", "approve", admin)
    assert response.status_code == 404
    assert requirements_for(db, other["id"])["budget"].status == RequirementStatus.pending


def test_approve_missing_club_404(client, admin):
    assert review(client, 999999, "budget", "approve", admin).status_code == 404


def test_approve_unknown_type_422(client, under_review, admin):
    assert review(client, under_review["id"], "nope", "approve", admin).status_code == 422


def test_approve_document_without_link_conflicts(client, db, under_review, admin):
    requirement = requirements_for(db, under_review["id"])["budget"]
    requirement.status = RequirementStatus.pending
    requirement.link_url = None
    db.commit()
    assert review(client, under_review["id"], "budget", "approve", admin).status_code == 409


def test_review_only_while_under_review(client, draft, admin):
    assert review(client, draft["id"], "exec_onboarding", "approve", admin).status_code == 409
    assert (
        review(
            client, draft["id"], "exec_onboarding", "reject", admin, json={"note": "x"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize("body", [None, {}, {"note": ""}, {"note": "   "}])
def test_reject_requires_note(client, db, under_review, admin, body):
    response = review(client, under_review["id"], "budget", "reject", admin, json=body)
    assert response.status_code == 422
    assert requirements_for(db, under_review["id"])["budget"].status == RequirementStatus.submitted


def test_reject_with_note(client, db, under_review, admin):
    response = review(
        client, under_review["id"], "budget", "reject", admin, json={"note": " Totals missing "}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["reviewer_note"] == "Totals missing"


# --- requirement history ---------------------------------------------------


def requirement_events(db, club_id):
    return (
        db.query(ClubEvent)
        .filter(ClubEvent.club_id == club_id, ClubEvent.requirement_id.is_not(None))
        .order_by(ClubEvent.id)
        .all()
    )


def test_set_link_records_history(client, db, draft, lead):
    set_link(client, draft["id"], "budget", lead, "https://docs.example.com/budget-v1")
    [event] = requirement_events(db, draft["id"])
    assert event.event_type == "requirement_submitted"
    assert event.requirement_id == requirements_for(db, draft["id"])["budget"].id
    assert event.actor_id == lead.id
    assert event.link_url == "https://docs.example.com/budget-v1"
    assert event.from_status == event.to_status == ClubStatus.drafting


def test_replacing_a_link_keeps_both_versions_in_history(client, db, draft, lead):
    set_link(client, draft["id"], "budget", lead, "https://docs.example.com/v1")
    set_link(client, draft["id"], "budget", lead, "https://docs.example.com/v2")
    assert [e.link_url for e in requirement_events(db, draft["id"])] == [
        "https://docs.example.com/v1",
        "https://docs.example.com/v2",
    ]
    assert requirements_for(db, draft["id"])["budget"].link_url == "https://docs.example.com/v2"


def test_reject_records_history_with_note(client, db, under_review, admin):
    review(client, under_review["id"], "budget", "reject", admin, json={"note": " Totals missing "})
    [event] = requirement_events(db, under_review["id"])
    assert event.event_type == "requirement_rejected"
    assert event.requirement_id == requirements_for(db, under_review["id"])["budget"].id
    assert event.actor_id == admin.id
    assert event.note == "Totals missing"
    assert event.from_status == event.to_status == ClubStatus.under_review


@pytest.mark.parametrize(("body", "note"), [(None, None), ({"note": " Nice "}, "Nice")])
def test_approve_records_history(client, db, under_review, admin, body, note):
    review(client, under_review["id"], "exec_onboarding", "approve", admin, json=body)
    [event] = requirement_events(db, under_review["id"])
    assert event.event_type == "requirement_approved"
    assert event.requirement_id == requirements_for(db, under_review["id"])["exec_onboarding"].id
    assert event.actor_id == admin.id
    assert event.note == note


def test_rejection_reason_survives_new_link(client, db, under_review, lead, admin):
    """The gap the M1 walkthrough found: replacing a rejected document clears the
    requirement's reviewer_note, but the reason must still be in history."""
    club_id = under_review["id"]
    review(client, club_id, "budget", "reject", admin, json={"note": "Line items don't sum"})
    client.post(f"/clubs/{club_id}/request-changes", json={"note": "Fix it"}, headers=auth(admin))
    set_link(client, club_id, "budget", lead, "https://docs.example.com/budget-v2")

    assert requirements_for(db, club_id)["budget"].reviewer_note is None
    assert [(e.event_type, e.note) for e in requirement_events(db, club_id)] == [
        ("requirement_rejected", "Line items don't sum"),
        ("requirement_submitted", None),
    ]


def test_approving_twice_conflicts_and_writes_one_event(client, db, under_review, admin):
    assert review(client, under_review["id"], "exec_onboarding", "approve", admin).status_code == 200
    second = review(client, under_review["id"], "exec_onboarding", "approve", admin)
    assert second.status_code == 409
    assert "already approved" in second.json()["detail"]
    assert len(requirement_events(db, under_review["id"])) == 1


def test_refused_actions_write_no_history(client, db, under_review, lead, other_lead, admin):
    # under_review is built from the draft fixture, so use a separate club for drafting.
    drafting = create_club(client, lead, name="Still Drafting")
    responses = [
        set_link(client, drafting["id"], "exec_onboarding", lead),  # checklist
        set_link(client, drafting["id"], "budget", other_lead),  # not owner
        set_link(client, under_review["id"], "budget", lead),  # already submitted
        review(client, under_review["id"], "budget", "approve", lead),  # wrong role
        review(client, under_review["id"], "budget", "reject", admin, json={"note": " "}),
        review(client, drafting["id"], "exec_onboarding", "approve", admin),  # not under review
    ]
    assert [r.status_code for r in responses] == [409, 403, 409, 403, 422, 409]
    assert requirement_events(db, drafting["id"]) == []
    assert requirement_events(db, under_review["id"]) == []
