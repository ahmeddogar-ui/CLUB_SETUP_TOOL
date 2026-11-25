"""Concurrent requests on one club. Unlike the rest of the suite these tests
commit for real, because a lock only matters between separate transactions."""

import threading

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.exceptions import Conflict
from app.models import (
    ClubEvent,
    Clubs,
    ClubStatus,
    RequirementStatus,
    User,
    UserRole,
)
from app.services.clubs import submit_club_for_user
from tests.conftest import make_club, make_user

PARALLEL_REQUESTS = 10


@pytest.fixture
def committed_db(engine):
    """A session whose commits are real. The test database is disposable, so
    afterwards every table is emptied. TRUNCATE doesn't fire the append-only
    trigger on club_events, which only guards row-level UPDATE and DELETE."""
    with Session(engine) as session:
        yield session
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE users, clubs, requirements, club_events, refresh_tokens "
                "RESTART IDENTITY CASCADE"
            )
        )


def test_parallel_submits_on_one_club_succeed_exactly_once(engine, committed_db):
    lead = make_user(committed_db, UserRole.club_lead)
    club = make_club(committed_db, lead, requirement_status=RequirementStatus.submitted)
    club_id, lead_id = club.id, lead.id

    start_together = threading.Barrier(PARALLEL_REQUESTS)
    outcomes: list[str] = []

    def submit() -> None:
        with Session(engine) as session:
            user = session.get_one(User, lead_id)
            start_together.wait()
            try:
                submit_club_for_user(session, club_id, user)
                outcomes.append("submitted")
            except Conflict:
                outcomes.append("conflict")

    threads = [threading.Thread(target=submit) for _ in range(PARALLEL_REQUESTS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("submitted") == 1
    assert outcomes.count("conflict") == PARALLEL_REQUESTS - 1
    submitted_events = committed_db.scalar(
        select(func.count())
        .select_from(ClubEvent)
        .where(ClubEvent.club_id == club_id, ClubEvent.event_type == "submitted")
    )
    assert submitted_events == 1
    committed_db.expire_all()
    assert committed_db.get_one(Clubs, club_id).status == ClubStatus.submitted
