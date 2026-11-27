from zoneinfo import ZoneInfo

import pytest

from app.exceptions import Conflict
from app.models import (
    Clubs,
    ClubStatus,
    Event,
    Request,
    RequestStatus,
    RequestType,
    User,
    UserRole,
)
from app.seed import (
    DEMO_ADMIN_EMAIL,
    DEMO_FINANCE_EMAIL,
    DEMO_LEAD_EMAIL,
    DEMO_LEADS,
    demo_data_exists,
    seed_demo,
)


def user_by_email(db, email):
    return db.query(User).filter(User.email == email).one()


def seeded_clubs(db):
    """Only the seed's clubs, whatever else the test database holds."""
    emails = [email for _, email in DEMO_LEADS]
    return (
        db.query(Clubs)
        .join(User, User.id == Clubs.submitter_id)
        .filter(User.email.in_(emails))
        .all()
    )


def test_seed_creates_a_demo_admin_and_a_demo_club_lead(db):
    seed_demo(db)
    assert user_by_email(db, DEMO_ADMIN_EMAIL).role == UserRole.admin
    assert user_by_email(db, DEMO_LEAD_EMAIL).role == UserRole.club_lead


def test_seed_fills_every_status_with_about_fifteen_clubs(db):
    seed_demo(db)
    clubs = seeded_clubs(db)
    assert len(clubs) >= 15
    assert {club.status for club in clubs} == set(ClubStatus)


def test_seed_spreads_clubs_across_several_owners(db):
    seed_demo(db)
    assert len({club.submitter_id for club in seeded_clubs(db)}) >= 3


def test_the_demo_lead_has_clubs_in_several_statuses(db):
    seed_demo(db)
    lead = user_by_email(db, DEMO_LEAD_EMAIL)
    statuses = {club.status for club in db.query(Clubs).filter_by(submitter_id=lead.id)}
    assert len(statuses) >= 4


def test_seeded_clubs_were_last_updated_at_different_times(db):
    seed_demo(db)
    assert len({club.updated_at.date() for club in seeded_clubs(db)}) >= 5


def test_seeded_clubs_have_real_history(db):
    seed_demo(db)
    approved = next(
        club for club in seeded_clubs(db) if club.status == ClubStatus.approved
    )
    event_types = {
        event.event_type for event in db.query(Event).filter_by(club_id=approved.id)
    }
    assert {"created", "submitted", "review_started", "approved"} <= event_types


def test_seeding_twice_is_refused(db):
    seed_demo(db)
    with pytest.raises(Conflict):
        seed_demo(db)


def test_demo_data_exists_only_after_seeding(db):
    assert demo_data_exists(db) is False
    seed_demo(db)
    assert demo_data_exists(db) is True


def test_seed_adds_a_demo_finance_approver_through_the_users_page_rule(db):
    seed_demo(db)
    finance = user_by_email(db, DEMO_FINANCE_EMAIL)
    assert finance.role == UserRole.finance_approver
    promotion = (
        db.query(Event)
        .filter(Event.subject_user_id == finance.id, Event.event_type == "role_changed")
        .one()
    )
    assert promotion.note == "Club lead → Finance approver"


def test_seed_puts_requests_of_both_types_in_every_status(db):
    seed_demo(db)
    rows = (
        db.query(Request.request_type, Request.status)
        .join(Clubs, Clubs.id == Request.club_id)
        .join(User, User.id == Clubs.submitter_id)
        .filter(User.email.in_([email for _, email in DEMO_LEADS]))
        .all()
    )
    for request_type in RequestType:
        assert {status for kind, status in rows if kind == request_type} == set(
            RequestStatus
        )


def test_seed_starts_conversations(db):
    seed_demo(db)
    comments = db.query(Event).filter(Event.event_type == "comment_posted").count()
    assert comments >= 4


def test_seed_books_rooms_at_toronto_local_hours(db):
    """UTM is in Toronto: "Author talk" is listed for 18:00, so it starts at
    18:00 there, whatever the server's clock or the date's DST offset."""
    seed_demo(db)
    talk = db.query(Request).filter(Request.title == "Author talk").one()
    starts = talk.booked_during.lower.astimezone(ZoneInfo("America/Toronto"))
    assert (starts.hour, starts.minute) == (18, 0)
