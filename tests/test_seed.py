import pytest

from app.exceptions import Conflict
from app.models import ClubEvent, Clubs, ClubStatus, User, UserRole
from app.seed import DEMO_ADMIN_EMAIL, DEMO_LEAD_EMAIL, demo_data_exists, seed_demo


def user_by_email(db, email):
    return db.query(User).filter(User.email == email).one()


def test_seed_creates_a_demo_admin_and_a_demo_club_lead(db):
    seed_demo(db)
    assert user_by_email(db, DEMO_ADMIN_EMAIL).role == UserRole.admin
    assert user_by_email(db, DEMO_LEAD_EMAIL).role == UserRole.club_lead


def test_seed_gives_the_lead_clubs_in_different_statuses(db):
    seed_demo(db)
    lead = user_by_email(db, DEMO_LEAD_EMAIL)
    statuses = {club.status for club in db.query(Clubs).filter_by(submitter_id=lead.id)}
    assert statuses == {ClubStatus.drafting, ClubStatus.submitted, ClubStatus.approved}


def test_seeded_clubs_have_real_history(db):
    seed_demo(db)
    lead = user_by_email(db, DEMO_LEAD_EMAIL)
    approved = (
        db.query(Clubs)
        .filter_by(submitter_id=lead.id, status=ClubStatus.approved)
        .one()
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
