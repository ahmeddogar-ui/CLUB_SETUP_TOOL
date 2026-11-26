import pytest

from app.exceptions import Conflict
from app.models import ClubEvent, Clubs, ClubStatus, User, UserRole
from app.seed import (
    DEMO_ADMIN_EMAIL,
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
        event.event_type for event in db.query(ClubEvent).filter_by(club_id=approved.id)
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
