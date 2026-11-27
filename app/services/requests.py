"""The request engine: create, edit, act on and list requests of every type.
Like clubs, every write locks the request row first and commits once with its
history event."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from psycopg2.errors import ExclusionViolation
from sqlalchemy import ColumnElement, ScalarSelect, func, or_, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.exceptions import Conflict, Forbidden, NotFound
from app.listing import Page, paginate
from app.models import (
    AWAITING_APPROVAL_STATUSES,
    Clubs,
    ClubStatus,
    Event,
    EventType,
    FundingLineItem,
    Request,
    RequestApproval,
    RequestStatus,
    RequestType,
    Room,
    User,
    UserRole,
)
from app.request_transitions import (
    ACTIONS,
    EVENT_TYPES,
    NEXT_STATUS,
    Actor,
    RequestAction,
)
from app.request_types import (
    APPROVAL_STEPS,
    FundingDetails,
    RequestDetails,
    RoomBookingDetails,
)
from app.services.clubs import ensure_owner, get_club

EDITABLE_STATUSES = (RequestStatus.draft, RequestStatus.changes_requested)
# Moving a booking towards approval makes no sense once its time has come.
TIME_BOUND_ACTIONS = (
    RequestAction.submit,
    RequestAction.start_review,
    RequestAction.approve,
)
NO_DOUBLE_BOOKING_CONSTRAINT = "no_double_booking"


@dataclass(frozen=True)
class Approval:
    step: int
    approver_name: str
    approved_at: datetime
    note: str | None


@dataclass(frozen=True)
class RequestView:
    """A request with everything its page shows, for one viewer."""

    request: Request
    club_name: str
    created_by_name: str
    approvals: list[Approval]
    line_items: list[FundingLineItem]
    room: Room | None
    allowed_actions: list[RequestAction]
    can_edit: bool


@dataclass(frozen=True)
class RequestSummary:
    request: Request
    club_name: str
    created_by_name: str
    total_cents: int | None
    room_name: str | None


class RequestSort(str, Enum):
    # Longest waiting first: the review queue.
    oldest = "oldest"
    newest = "newest"


@dataclass(frozen=True)
class RequestFilters:
    club_id: int | None = None
    statuses: tuple[RequestStatus, ...] = ()
    # Only what waits for the viewer's role at its current step.
    awaiting_me: bool = False
    oldest_first: bool = False


# --- visibility -------------------------------------------------------------


def _types_approved_by(user: User) -> list[RequestType]:
    return [
        request_type
        for request_type, steps in APPROVAL_STEPS.items()
        if user.role in steps
    ]


def _can_see(user: User, request: Request, club_owner_id: int) -> bool:
    """The club's lead, and anyone who approves a step of its type: admins see
    every request, finance approvers only funding."""
    return club_owner_id == user.id or request.request_type in _types_approved_by(user)


def _visible_to(user: User) -> ColumnElement[bool]:
    """_can_see as a filter; the query must join Clubs."""
    return or_(
        Clubs.submitter_id == user.id,
        Request.request_type.in_(_types_approved_by(user)),
    )


# --- reading ----------------------------------------------------------------


def _total_cents() -> ScalarSelect[int]:
    """Per request, run only for the rows on the page (a correlated subquery)."""
    return (
        select(func.sum(FundingLineItem.amount_cents))
        .where(FundingLineItem.request_id == Request.id)
        .correlate(Request)
        .scalar_subquery()
    )


def list_requests(
    db: Session, user: User, filters: RequestFilters, limit: int, offset: int
) -> Page[RequestSummary]:
    creator = aliased(User)
    query = (
        db.query(Request, Clubs.name, creator.name, _total_cents(), Room.name)
        .join(Clubs, Clubs.id == Request.club_id)
        .join(creator, creator.id == Request.created_by_id)
        .outerjoin(Room, Room.id == Request.room_id)
        .filter(_visible_to(user))
    )
    if filters.club_id is not None:
        query = query.filter(Request.club_id == filters.club_id)
    if filters.statuses:
        query = query.filter(Request.status.in_(filters.statuses))
    if filters.awaiting_me:
        query = query.filter(Request.awaiting_role == user.role)

    if filters.oldest_first:
        query = query.order_by(Request.updated_at.asc(), Request.id.asc())
    else:
        query = query.order_by(Request.updated_at.desc(), Request.id.desc())

    page = paginate(query, limit, offset)
    return Page(
        items=[RequestSummary(*row) for row in page.items],
        total=page.total,
    )


def get_request_view(db: Session, request_id: int, user: User) -> RequestView:
    request, club = _get_with_club(db, request_id, for_update=False)
    _ensure_visible(user, request, club)
    return _view(db, request, club, user)


def list_request_events(
    db: Session, request_id: int, user: User
) -> list[tuple[Event, str]]:
    """Newest first, with the actor's name; served by idx_events_request_time."""
    request, club = _get_with_club(db, request_id, for_update=False)
    _ensure_visible(user, request, club)
    return (
        db.query(Event, User.name)
        .join(User, User.id == Event.actor_id)
        .filter(Event.request_id == request.id)
        .order_by(Event.created_at.desc(), Event.id.desc())
        .tuples()
        .all()
    )


def list_rooms(db: Session) -> list[Room]:
    return db.query(Room).order_by(Room.name).all()


# --- writing ----------------------------------------------------------------


def create_request(
    db: Session, club_id: int, user: User, title: str, details: RequestDetails
) -> RequestView:
    """A draft, by the club's lead, for an approved club only."""
    club = get_club(db, club_id)
    ensure_owner(club, user)
    if club.status != ClubStatus.approved:
        raise Conflict("Only an approved club can make requests")

    request = Request(
        club_id=club.id,
        request_type=details.request_type,
        title=title,
        status=RequestStatus.draft,
        created_by_id=user.id,
    )
    db.add(request)
    # Before the first flush: a booking's row must arrive with its room and time.
    _store_details(db, request, details)
    db.flush()
    _record(db, request, user, EventType.request_created)
    _commit(db, request)
    return _view(db, request, club, user)


def update_request(
    db: Session,
    request_id: int,
    user: User,
    title: str | None,
    details: RequestDetails | None,
) -> RequestView:
    """Ownership before status, so a stranger never learns a request's state."""
    request, club = _get_with_club(db, request_id, for_update=True)
    ensure_owner(club, user)
    new_room_id = details.room_id if isinstance(details, RoomBookingDetails) else None
    _lock_rooms(db, {request.room_id, new_room_id})
    if request.status not in EDITABLE_STATUSES:
        raise Conflict(
            "Only a draft, or a request with changes requested, can be edited"
        )
    if details is not None and details.request_type != request.request_type:
        raise Conflict("A request's type can't change")

    if title is not None:
        request.title = title
    if details is not None:
        _store_details(db, request, details)
    request.updated_at = datetime.now(UTC)
    _commit(db, request)
    return _view(db, request, club, user)


def act_on_request(
    db: Session,
    request_id: int,
    user: User,
    action: RequestAction,
    note: str | None = None,
) -> RequestView:
    """Checks, in order: who may see it (403/404), whether the action fits its
    status (409), whether this user may take it (403). The row lock makes two
    concurrent actions run one after the other, so the second sees the first's
    result: two approvals of one step can't both succeed."""
    request, club = _get_with_club(db, request_id, for_update=True)
    _lock_rooms(db, {request.room_id})
    _ensure_visible(user, request, club)

    from_statuses, actor = ACTIONS[action]
    if request.status not in from_statuses:
        raise Conflict(
            f"Cannot {action.value.replace('_', ' ')} a request that is "
            f"{request.status.value.replace('_', ' ')}"
        )
    if not _is_actor(user, request, club, actor):
        raise Forbidden("You may not take this action on this request")
    refusal = _refusal(action, request)
    if refusal:
        raise Conflict(refusal)

    steps = APPROVAL_STEPS[request.request_type]
    if action == RequestAction.approve:
        event_type = _approve_current_step(db, request, user, steps, note)
    else:
        request.status = NEXT_STATUS[action]
        event_type = EVENT_TYPES[action]
        if action == RequestAction.submit:
            # A new round: every step must approve again, from the first.
            request.round += 1
            request.awaiting_role = steps[0]
        elif request.status not in AWAITING_APPROVAL_STATUSES:
            request.awaiting_role = None

    request.updated_at = datetime.now(UTC)
    _record(db, request, user, event_type, note)
    _commit(db, request)
    return _view(db, request, club, user)


def _approve_current_step(
    db: Session,
    request: Request,
    approver: User,
    steps: tuple[UserRole, ...],
    note: str | None,
) -> EventType:
    step = _approved_step_count(db, request)
    db.add(
        RequestApproval(
            request_id=request.id,
            round=request.round,
            step=step,
            approver_id=approver.id,
            note=note,
        )
    )
    if step + 1 == len(steps):
        request.status = RequestStatus.approved
        request.awaiting_role = None
        return EventType.request_approved
    request.awaiting_role = steps[step + 1]
    return EventType.request_step_approved


# --- helpers ----------------------------------------------------------------


def _get_with_club(
    db: Session, request_id: int, *, for_update: bool
) -> tuple[Request, Clubs]:
    query = db.query(Request).filter(Request.id == request_id)
    if for_update:
        # populate_existing() replaces any stale copy this session holds.
        query = query.with_for_update().populate_existing()
    request = query.first()
    if request is None:
        raise NotFound("Request not found")
    return request, get_club(db, request.club_id)


def _lock_rooms(db: Session, room_ids: set[int | None]) -> None:
    """Locks each room, in id order, so two moves between the same rooms
    queue instead of deadlocking."""
    for room_id in sorted(room_id for room_id in room_ids if room_id is not None):
        _lock_room(db, room_id)


def _lock_room(db: Session, room_id: int) -> Room:
    """Bookings of one room take their slot one at a time. Without this, two
    bookings racing for one slot each wait on the other's exclusion-constraint
    check and Postgres aborts one as a deadlock; with it, the second sees the
    first's committed row and gets a clean violation. The constraint is still
    what guarantees no double booking."""
    room = (
        db.query(Room)
        .filter(Room.id == room_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if room is None:
        raise NotFound("Room not found")
    return room


def _ensure_visible(user: User, request: Request, club: Clubs) -> None:
    if not _can_see(user, request, club.submitter_id):
        raise Forbidden("Not your request")


def _is_actor(user: User, request: Request, club: Clubs, actor: Actor) -> bool:
    if actor == Actor.owner:
        return club.submitter_id == user.id
    return request.awaiting_role == user.role


def _refusal(action: RequestAction, request: Request) -> str | None:
    """Rules beyond status and role, for the actions that would otherwise
    rewrite what already happened or let time run past a booking."""
    # A booking's range is always bounded (ck_requests_booking_bounded).
    starts_at = request.booked_during.lower if request.booked_during else None
    started = starts_at is not None and starts_at <= datetime.now(UTC)
    if action in TIME_BOUND_ACTIONS and started:
        return "This booking has already started"
    if action == RequestAction.cancel and request.status == RequestStatus.approved:
        if request.request_type == RequestType.funding:
            return "Approved funding can't be cancelled"
        if started:
            return "This booking has already started"
    return None


def _allowed_actions(user: User, request: Request, club: Clubs) -> list[RequestAction]:
    """What this user may do now; the UI shows exactly these."""
    return [
        action
        for action, (from_statuses, actor) in ACTIONS.items()
        if request.status in from_statuses
        and _is_actor(user, request, club, actor)
        and _refusal(action, request) is None
    ]


def _can_edit(user: User, request: Request, club: Clubs) -> bool:
    return club.submitter_id == user.id and request.status in EDITABLE_STATUSES


def _approved_step_count(db: Session, request: Request) -> int:
    return (
        db.query(func.count(RequestApproval.id))
        .filter(
            RequestApproval.request_id == request.id,
            RequestApproval.round == request.round,
        )
        .scalar()
        or 0
    )


def _store_details(db: Session, request: Request, details: RequestDetails) -> None:
    """Where each type keeps its own data."""
    match details:
        case FundingDetails():
            db.flush()  # The line items need the request's id.
            db.query(FundingLineItem).filter(
                FundingLineItem.request_id == request.id
            ).delete()
            db.add_all(
                FundingLineItem(
                    request_id=request.id,
                    position=position,
                    description=item.description,
                    amount_cents=item.amount_cents,
                )
                for position, item in enumerate(details.line_items)
            )
        case RoomBookingDetails():
            # No autoflush: a new booking can't be written before it has a room.
            with db.no_autoflush:
                _lock_room(db, details.room_id)
            request.room_id = details.room_id
            # [start, end): a booking ending at 11:00 and one starting then fit.
            request.booked_during = Range(
                details.starts_at, details.ends_at, bounds="[)"
            )


def _record(
    db: Session,
    request: Request,
    actor: User,
    event_type: EventType,
    note: str | None = None,
) -> None:
    db.add(
        Event(
            club_id=request.club_id,
            request_id=request.id,
            actor_id=actor.id,
            event_type=event_type,
            note=note,
        )
    )


def _commit(db: Session, request: Request) -> None:
    """Commits, turning the database's no-double-booking refusal into a
    Conflict that names the room. Read the name first: a failed commit
    expires every loaded object."""
    with db.no_autoflush:
        room = db.get(Room, request.room_id) if request.room_id is not None else None
    room_name = room.name if room is not None else ""
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if (
            isinstance(error.orig, ExclusionViolation)
            and error.orig.diag.constraint_name == NO_DOUBLE_BOOKING_CONSTRAINT
        ):
            raise Conflict(
                f"{room_name} is already booked for part of that time. "
                "Choose another time or room."
            ) from error
        raise


def _view(db: Session, request: Request, club: Clubs, user: User) -> RequestView:
    db.refresh(request)
    creator = db.get_one(User, request.created_by_id)
    approvals = [
        Approval(approval.step, name, approval.approved_at, approval.note)
        for approval, name in db.query(RequestApproval, User.name)
        .join(User, User.id == RequestApproval.approver_id)
        .filter(
            RequestApproval.request_id == request.id,
            RequestApproval.round == request.round,
        )
        .order_by(RequestApproval.step)
        .tuples()
    ]
    line_items = (
        db.query(FundingLineItem)
        .filter(FundingLineItem.request_id == request.id)
        .order_by(FundingLineItem.position)
        .all()
    )
    room = db.get(Room, request.room_id) if request.room_id is not None else None
    return RequestView(
        request=request,
        club_name=club.name,
        created_by_name=creator.name,
        approvals=approvals,
        line_items=line_items,
        room=room,
        allowed_actions=_allowed_actions(user, request, club),
        can_edit=_can_edit(user, request, club),
    )
