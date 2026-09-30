"""Ticket 16: the transition service, called directly (no HTTP)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import (
    ClubEvent,
    Clubs,
    ClubStatus,
    RequirementStatus,
    User,
    UserRole,
)
from app.transitions import InvalidTransition, TransitionBlocked, attempt_transition
from tests.conftest import (
    approve_all_requirements,
    create_club,
    provide_all_documents,
    requirements_for,
)


def load_club(db, club_id) -> Clubs:
    return db.get(Clubs, club_id)


def transition_events(db, club_id) -> list[ClubEvent]:
    return (
        db.query(ClubEvent)
        .filter(ClubEvent.club_id == club_id, ClubEvent.event_type != "created")
        .order_by(ClubEvent.id)
        .all()
    )


@pytest.fixture
def draft(client, db, lead):
    club = create_club(client, lead)
    return load_club(db, club["id"])


@pytest.fixture
def submitted(db, draft, lead):
    provide_all_documents(db, draft.id)
    return attempt_transition(db, draft, ClubStatus.submitted, lead)


@pytest.fixture
def under_review(db, submitted, admin):
    return attempt_transition(db, submitted, ClubStatus.under_review, admin)


# --- every legal transition ------------------------------------------------


def test_drafting_to_submitted(db, draft, lead):
    provide_all_documents(db, draft.id)
    club = attempt_transition(db, draft, ClubStatus.submitted, lead)
    assert club.status == ClubStatus.submitted
    [event] = transition_events(db, club.id)
    assert (event.from_status, event.to_status) == (ClubStatus.drafting, ClubStatus.submitted)
    assert event.event_type == "submitted"
    assert event.actor_id == lead.id


def test_submitted_to_under_review(db, submitted, admin):
    club = attempt_transition(db, submitted, ClubStatus.under_review, admin)
    assert club.status == ClubStatus.under_review
    event = transition_events(db, club.id)[-1]
    assert (event.from_status, event.to_status) == (ClubStatus.submitted, ClubStatus.under_review)
    assert len(transition_events(db, club.id)) == 2


def test_under_review_to_approved(db, under_review, admin):
    approve_all_requirements(db, under_review.id)
    club = attempt_transition(db, under_review, ClubStatus.approved, admin)
    assert club.status == ClubStatus.approved
    event = transition_events(db, club.id)[-1]
    assert (event.from_status, event.to_status) == (ClubStatus.under_review, ClubStatus.approved)
    assert len(transition_events(db, club.id)) == 3


@pytest.mark.parametrize("to_status", [ClubStatus.changes_requested, ClubStatus.rejected])
def test_under_review_to_note_required_statuses(db, under_review, admin, to_status):
    club = attempt_transition(db, under_review, to_status, admin, "  Budget is missing totals  ")
    assert club.status == to_status
    event = transition_events(db, club.id)[-1]
    assert (event.from_status, event.to_status) == (ClubStatus.under_review, to_status)
    assert event.note == "Budget is missing totals"
    assert len(transition_events(db, club.id)) == 3


def test_changes_requested_to_submitted(db, under_review, admin, lead):
    club = attempt_transition(db, under_review, ClubStatus.changes_requested, admin, "fix it")
    club = attempt_transition(db, club, ClubStatus.submitted, lead)
    assert club.status == ClubStatus.submitted
    event = transition_events(db, club.id)[-1]
    assert event.event_type == "resubmitted"
    assert (event.from_status, event.to_status) == (ClubStatus.changes_requested, ClubStatus.submitted)


def test_full_resubmit_loop_keeps_all_history(db, under_review, admin, lead):
    club = attempt_transition(db, under_review, ClubStatus.changes_requested, admin, "round 1")
    club = attempt_transition(db, club, ClubStatus.submitted, lead)
    club = attempt_transition(db, club, ClubStatus.under_review, admin)
    club = attempt_transition(db, club, ClubStatus.changes_requested, admin, "round 2")

    events = transition_events(db, club.id)
    assert [e.to_status for e in events] == [
        ClubStatus.submitted,
        ClubStatus.under_review,
        ClubStatus.changes_requested,
        ClubStatus.submitted,
        ClubStatus.under_review,
        ClubStatus.changes_requested,
    ]
    assert [e.note for e in events if e.to_status == ClubStatus.changes_requested] == [
        "round 1",
        "round 2",
    ]


# --- illegal transitions ---------------------------------------------------


def _force_status(db, club, status):
    club.status = status
    db.commit()
    return club


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (ClubStatus.drafting, ClubStatus.approved),  # skipping steps
        (ClubStatus.drafting, ClubStatus.under_review),  # skipping a step
        (ClubStatus.approved, ClubStatus.submitted),  # out of a terminal status
        (ClubStatus.rejected, ClubStatus.under_review),  # out of a terminal status
        (ClubStatus.submitted, ClubStatus.submitted),  # repeating a transition
        (ClubStatus.under_review, ClubStatus.under_review),  # repeating a transition
        (ClubStatus.under_review, ClubStatus.drafting),  # moving backward
    ],
)
def test_illegal_transitions_rejected_and_nothing_changes(
    db, draft, admin, lead, from_status, to_status
):
    club = _force_status(db, draft, from_status)
    before = len(transition_events(db, club.id))

    for actor in (lead, admin):
        with pytest.raises(InvalidTransition):
            attempt_transition(db, club, to_status, actor, "note")

    db.expire_all()
    assert load_club(db, club.id).status == from_status
    assert len(transition_events(db, club.id)) == before


# --- role checks -----------------------------------------------------------


def test_club_lead_cannot_start_review_on_own_club(db, submitted, lead):
    with pytest.raises(InvalidTransition, match="club_lead may not"):
        attempt_transition(db, submitted, ClubStatus.under_review, lead)


@pytest.mark.parametrize(
    ("to_status", "note"),
    [
        (ClubStatus.approved, None),
        (ClubStatus.rejected, "no"),
        (ClubStatus.changes_requested, "fix"),
    ],
)
def test_club_lead_cannot_perform_admin_decisions(db, under_review, lead, to_status, note):
    approve_all_requirements(db, under_review.id)
    with pytest.raises(InvalidTransition):
        attempt_transition(db, under_review, to_status, lead, note)
    assert load_club(db, under_review.id).status == ClubStatus.under_review


def test_admin_cannot_submit_on_behalf_of_lead(db, draft, admin):
    provide_all_documents(db, draft.id)
    with pytest.raises(InvalidTransition, match="admin may not"):
        attempt_transition(db, draft, ClubStatus.submitted, admin)


# --- submit guard ----------------------------------------------------------


def test_submit_blocked_when_core_info_missing(db, draft, lead):
    provide_all_documents(db, draft.id)
    draft.description = "   "
    db.commit()
    with pytest.raises(TransitionBlocked, match="description"):
        attempt_transition(db, draft, ClubStatus.submitted, lead)
    assert load_club(db, draft.id).status == ClubStatus.drafting


def test_submit_blocked_when_document_missing_names_it(db, draft, lead):
    provide_all_documents(db, draft.id)
    requirement = requirements_for(db, draft.id)["constitution"]
    requirement.status = RequirementStatus.pending
    requirement.link_url = None
    db.commit()

    with pytest.raises(TransitionBlocked) as exc:
        attempt_transition(db, draft, ClubStatus.submitted, lead)
    assert "constitution" in str(exc.value)
    assert "exec_list" not in str(exc.value)


def test_submit_blocked_when_document_rejected(db, draft, lead):
    provide_all_documents(db, draft.id)
    requirements_for(db, draft.id)["budget"].status = RequirementStatus.rejected
    db.commit()
    with pytest.raises(TransitionBlocked, match="budget"):
        attempt_transition(db, draft, ClubStatus.submitted, lead)


def test_submit_allowed_with_checklist_items_still_pending(db, draft, lead):
    provide_all_documents(db, draft.id)
    requirements = requirements_for(db, draft.id)
    assert requirements["bank_account_setup"].status == RequirementStatus.pending
    assert requirements["exec_onboarding"].status == RequirementStatus.pending

    club = attempt_transition(db, draft, ClubStatus.submitted, lead)
    assert club.status == ClubStatus.submitted


# --- approve guard ---------------------------------------------------------


@pytest.mark.parametrize(
    ("requirement_type", "status"),
    [
        ("budget", RequirementStatus.submitted),  # provided, not yet approved
        ("budget", RequirementStatus.rejected),
        ("exec_onboarding", RequirementStatus.pending),  # checklist item
        ("bank_account_setup", RequirementStatus.rejected),
    ],
)
def test_approve_blocked_by_any_unapproved_requirement(
    db, under_review, admin, requirement_type, status
):
    approve_all_requirements(db, under_review.id)
    requirements_for(db, under_review.id)[requirement_type].status = status
    db.commit()

    with pytest.raises(TransitionBlocked) as exc:
        attempt_transition(db, under_review, ClubStatus.approved, admin)
    assert requirement_type in str(exc.value)
    assert load_club(db, under_review.id).status == ClubStatus.under_review


# --- note guard ------------------------------------------------------------


@pytest.mark.parametrize("to_status", [ClubStatus.changes_requested, ClubStatus.rejected])
@pytest.mark.parametrize("note", [None, "", "   ", "\n\t"])
def test_note_required(db, under_review, admin, to_status, note):
    with pytest.raises(TransitionBlocked, match="note is required"):
        attempt_transition(db, under_review, to_status, admin, note)
    assert load_club(db, under_review.id).status == ClubStatus.under_review


# --- atomicity & immutability ----------------------------------------------


def test_failed_event_write_rolls_back_status_change(db, submitted):
    # An admin whose id doesn't exist in users: the status update is valid, but
    # the event row violates its actor_id foreign key when the commit runs.
    ghost_admin = User(id=987654321, name="ghost", email="g@x.com", role=UserRole.admin)

    with pytest.raises(IntegrityError):
        attempt_transition(db, submitted, ClubStatus.under_review, ghost_admin)

    db.expire_all()
    assert load_club(db, submitted.id).status == ClubStatus.submitted
    assert all(e.to_status != ClubStatus.under_review for e in transition_events(db, submitted.id))


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE club_events SET note = 'rewritten' WHERE club_id = :club_id",
        "DELETE FROM club_events WHERE club_id = :club_id",
    ],
)
def test_history_rows_cannot_be_edited_or_deleted(db, submitted, statement):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text(statement), {"club_id": submitted.id})
    db.rollback()
    assert len(transition_events(db, submitted.id)) == 1
