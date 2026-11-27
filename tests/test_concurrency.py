"""Concurrent requests on one club. Unlike the rest of the suite these tests
commit for real, because a lock only matters between separate transactions."""

import threading
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import Conflict, Forbidden
from app.models import (
    Clubs,
    ClubStatus,
    Event,
    RequirementStatus,
    User,
    UserRole,
)
from app.services.clubs import submit_club_for_user
from app.services.users import change_role
from tests.conftest import make_club, make_user

PARALLEL_REQUESTS = 10
# Generous: each request takes milliseconds. A timeout turns a stuck thread into
# a test failure instead of a hung test run.
TIMEOUT_SECONDS = 10


def test_parallel_submits_on_one_club_succeed_exactly_once(engine, committed_db):
    lead = make_user(committed_db, UserRole.club_lead)
    club = make_club(committed_db, lead, requirement_status=RequirementStatus.submitted)
    club_id, lead_id = club.id, lead.id

    start_together = threading.Barrier(PARALLEL_REQUESTS, timeout=TIMEOUT_SECONDS)

    def submit() -> str:
        with Session(engine) as session:
            user = session.get_one(User, lead_id)
            start_together.wait()
            try:
                submit_club_for_user(session, club_id, user)
                return "submitted"
            except Conflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
        futures = [pool.submit(submit) for _ in range(PARALLEL_REQUESTS)]
        # result() re-raises any unexpected error in this thread.
        outcomes = [future.result(timeout=TIMEOUT_SECONDS) for future in futures]

    assert outcomes.count("submitted") == 1
    assert outcomes.count("conflict") == PARALLEL_REQUESTS - 1
    submitted_events = committed_db.scalar(
        select(func.count())
        .select_from(Event)
        .where(Event.club_id == club_id, Event.event_type == "submitted")
    )
    assert submitted_events == 1
    committed_db.expire_all()
    assert committed_db.get_one(Clubs, club_id).status == ClubStatus.submitted


def test_two_admins_demoting_each_other_leave_one_admin(engine, committed_db):
    first = make_user(committed_db, UserRole.admin)
    second = make_user(committed_db, UserRole.admin)
    pairs = [(first.id, second.id), (second.id, first.id)]
    start_together = threading.Barrier(2, timeout=TIMEOUT_SECONDS)

    def demote(actor_id: int, target_id: int) -> str:
        with Session(engine) as session:
            actor = session.get_one(User, actor_id)
            start_together.wait()
            try:
                change_role(session, actor, target_id, UserRole.club_lead)
                return "demoted"
            except Forbidden:
                return "no longer an admin"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(demote, *pair) for pair in pairs]
        outcomes = [future.result(timeout=TIMEOUT_SECONDS) for future in futures]

    assert sorted(outcomes) == ["demoted", "no longer an admin"]
    committed_db.expire_all()
    roles = {
        committed_db.get_one(User, user_id).role for user_id in (first.id, second.id)
    }
    assert roles == {UserRole.admin, UserRole.club_lead}
