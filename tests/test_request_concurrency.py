"""Concurrent requests against the request engine. Like test_concurrency.py,
these commit for real: a lock or constraint only matters between transactions."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.exceptions import Conflict, Forbidden
from app.models import (
    ClubStatus,
    Request,
    RequestApproval,
    RequestStatus,
    RequestType,
    Room,
    User,
    UserRole,
)
from app.request_transitions import RequestAction
from app.request_types import RoomBookingDetails
from app.services.requests import act_on_request, update_request
from tests.conftest import make_club, make_user

# Twenty clubs try to book the same room for the same hour at the same moment.
PARALLEL_BOOKINGS = 20
TIMEOUT_SECONDS = 10


def run_together(count, work):
    """Runs work(i) on `count` threads released at once; returns the results."""
    start_together = threading.Barrier(count, timeout=TIMEOUT_SECONDS)

    def run(index):
        start_together.wait()
        return work(index)

    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(run, index) for index in range(count)]
        # result() re-raises any unexpected error in this thread.
        return [future.result(timeout=TIMEOUT_SECONDS) for future in futures]


def draft_booking(db: Session, lead: User, room: Room, starts: datetime) -> int:
    club = make_club(db, lead, status=ClubStatus.approved)
    request = Request(
        club_id=club.id,
        request_type=RequestType.room_booking,
        title="Meeting",
        status=RequestStatus.draft,
        created_by_id=lead.id,
        room_id=room.id,
        booked_during=Range(starts, starts + timedelta(hours=1), bounds="[)"),
    )
    db.add(request)
    db.commit()
    return request.id


def test_parallel_bookings_of_one_slot_succeed_exactly_once(engine, committed_db):
    room = committed_db.scalars(select(Room).order_by(Room.id)).first()
    starts = (datetime.now(UTC) + timedelta(days=2)).replace(
        minute=0, second=0, microsecond=0
    )
    leads = [
        make_user(committed_db, UserRole.club_lead) for _ in range(PARALLEL_BOOKINGS)
    ]
    request_ids = [draft_booking(committed_db, lead, room, starts) for lead in leads]
    lead_ids = [lead.id for lead in leads]

    def submit(index: int) -> str:
        with Session(engine) as session:
            user = session.get_one(User, lead_ids[index])
            try:
                act_on_request(session, request_ids[index], user, RequestAction.submit)
                return "booked"
            except Conflict:
                return "slot taken"

    outcomes = run_together(PARALLEL_BOOKINGS, submit)

    assert outcomes.count("booked") == 1
    assert outcomes.count("slot taken") == PARALLEL_BOOKINGS - 1
    holding = committed_db.scalar(
        select(func.count())
        .select_from(Request)
        .where(Request.id.in_(request_ids), Request.status == RequestStatus.submitted)
    )
    assert holding == 1


def test_parallel_approvals_of_one_step_succeed_exactly_once(engine, committed_db):
    lead = make_user(committed_db, UserRole.club_lead)
    admins = [make_user(committed_db, UserRole.admin) for _ in range(2)]
    club = make_club(committed_db, lead, status=ClubStatus.approved)
    request = Request(
        club_id=club.id,
        request_type=RequestType.funding,
        title="Social",
        status=RequestStatus.in_review,
        round=1,
        awaiting_role=UserRole.admin,
        created_by_id=lead.id,
    )
    committed_db.add(request)
    committed_db.commit()
    request_id, admin_ids = request.id, [admin.id for admin in admins]

    def approve(index: int) -> str:
        with Session(engine) as session:
            admin = session.get_one(User, admin_ids[index])
            try:
                act_on_request(session, request_id, admin, RequestAction.approve)
                return "approved"
            except Forbidden:
                # The first approval moved the request on to the finance step.
                return "not your step"

    outcomes = run_together(len(admins), approve)

    assert sorted(outcomes) == ["approved", "not your step"]
    approvals = committed_db.scalar(
        select(func.count())
        .select_from(RequestApproval)
        .where(RequestApproval.request_id == request_id)
    )
    assert approvals == 1


def test_two_bookings_swapping_rooms_at_once_dont_deadlock(engine, committed_db):
    """Each move locks both rooms in id order, so the two moves queue."""
    room_a, room_b = committed_db.scalars(select(Room).order_by(Room.id).limit(2)).all()
    starts = (datetime.now(UTC) + timedelta(days=3)).replace(
        minute=0, second=0, microsecond=0
    )
    lead = make_user(committed_db, UserRole.club_lead)
    first = draft_booking(committed_db, lead, room_a, starts)
    second = draft_booking(committed_db, lead, room_b, starts + timedelta(hours=2))
    moves = [(first, room_b), (second, room_a)]
    lead_id = lead.id

    def move(index: int) -> str:
        request_id, room = moves[index]
        with Session(engine) as session:
            user = session.get_one(User, lead_id)
            request = session.get_one(Request, request_id)
            details = RoomBookingDetails(
                request_type=RequestType.room_booking,
                room_id=room.id,
                starts_at=request.booked_during.lower,
                ends_at=request.booked_during.upper,
            )
            session.rollback()
            update_request(session, request_id, user, None, details)
            return "moved"

    assert run_together(2, move) == ["moved", "moved"]
