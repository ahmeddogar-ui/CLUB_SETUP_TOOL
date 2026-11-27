from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlalchemy import ColumnElement, ScalarSelect, func, select
from sqlalchemy.orm import Query, Session

from app.exceptions import Conflict, Forbidden, NotFound
from app.listing import contains
from app.models import (
    DOCUMENT_PROVIDED_STATUSES,
    Clubs,
    ClubStatus,
    Event,
    EventType,
    Requirement,
    RequirementKind,
    RequirementStatus,
    RequirementType,
    User,
    UserRole,
)
from app.transitions import attempt_transition

EDITABLE_STATUSES = (ClubStatus.drafting, ClubStatus.changes_requested)

INITIAL_REQUIREMENTS = (
    (RequirementType.constitution, RequirementKind.document),
    (RequirementType.exec_list, RequirementKind.document),
    (RequirementType.budget, RequirementKind.document),
    (RequirementType.advisor_form, RequirementKind.document),
    (RequirementType.bank_account_setup, RequirementKind.checklist),
    (RequirementType.exec_onboarding, RequirementKind.checklist),
)


class ClubSortField(str, Enum):
    name = "name"
    owner = "owner"
    status = "status"
    updated = "updated"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


# Status sorts in lifecycle order: Postgres orders an enum by declaration.
_SORT_COLUMNS = {
    ClubSortField.name: func.lower(Clubs.name),
    ClubSortField.owner: func.lower(User.name),
    ClubSortField.status: Clubs.status,
    ClubSortField.updated: Clubs.updated_at,
}


def create_club_for_user(db: Session, user: User, name: str, description: str) -> Clubs:
    # Only a club lead can ever submit a club, so a club created by anyone else
    # could never leave drafting.
    if user.role != UserRole.club_lead:
        raise Forbidden("Only club leads can create clubs")
    club = Clubs(
        name=name,
        description=description,
        submitter_id=user.id,
        status=ClubStatus.drafting,
    )
    db.add(club)
    db.flush()

    for requirement_type, kind in INITIAL_REQUIREMENTS:
        db.add(
            Requirement(
                club_id=club.id,
                requirement_type=requirement_type,
                kind=kind,
                status=RequirementStatus.pending,
            )
        )

    db.add(
        Event(
            club_id=club.id,
            actor_id=user.id,
            event_type=EventType.created,
            from_status=None,
            to_status=ClubStatus.drafting,
        )
    )

    db.commit()
    db.refresh(club)
    return club


@dataclass(frozen=True)
class ClubSummary:
    club: Clubs
    owner_name: str
    documents_provided: int
    documents_total: int


@dataclass(frozen=True)
class ClubPage:
    items: list[ClubSummary]
    # How many clubs match the filters, across all pages.
    total: int
    # Every club the user can see, by status, ignoring the filters.
    status_counts: dict[ClubStatus, int]


def _document_count(*conditions: ColumnElement[bool]) -> ScalarSelect[int]:
    """Per-club count of document requirements, run only for the clubs on the
    page (a correlated subquery), so a page costs the same queries at any size."""
    return (
        select(func.count())
        .where(
            Requirement.club_id == Clubs.id,
            Requirement.kind == RequirementKind.document,
            *conditions,
        )
        .correlate(Clubs)
        .scalar_subquery()
    )


def _visible_clubs(db: Session, user: User) -> Query[Clubs]:
    """Role scoping; the filters applied on top only ever narrow this set."""
    visible = db.query(Clubs)
    if user.role != UserRole.admin:
        visible = visible.filter(Clubs.submitter_id == user.id)
    return visible


def _filtered(
    visible: Query[Clubs], statuses: list[ClubStatus] | None, search: str | None
) -> Query[Clubs]:
    query = visible
    if statuses:
        query = query.filter(Clubs.status.in_(statuses))
    if search:
        query = query.filter(contains(Clubs.name, search))
    return query


def _summaries(
    query: Query[Clubs], sort: ClubSortField | None, order: SortOrder
) -> Query[Any]:
    """The filtered clubs in order, with owner name and document counts."""
    return _ordered(
        query.join(User, User.id == Clubs.submitter_id), sort, order
    ).add_columns(
        User.name,
        _document_count(Requirement.status.in_(DOCUMENT_PROVIDED_STATUSES)),
        _document_count(),
    )


def _to_summaries(rows: list[Any]) -> list[ClubSummary]:
    return [
        ClubSummary(club, owner_name, provided, total)
        for club, owner_name, provided, total in rows
    ]


def list_clubs_for_user(
    db: Session,
    user: User,
    statuses: list[ClubStatus] | None,
    sort: ClubSortField | None,
    order: SortOrder,
    search: str | None,
    limit: int,
    offset: int,
) -> ClubPage:
    visible = _visible_clubs(db, user)
    query = _filtered(visible, statuses, search)
    rows = _summaries(query, sort, order).limit(limit).offset(offset).all()
    return ClubPage(
        items=_to_summaries(rows),
        total=query.count(),
        status_counts=_count_by_status(visible),
    )


def export_clubs(
    db: Session,
    user: User,
    statuses: list[ClubStatus] | None,
    sort: ClubSortField | None,
    order: SortOrder,
    search: str | None,
) -> list[ClubSummary]:
    """Every club matching the filters, unpaged."""
    query = _filtered(_visible_clubs(db, user), statuses, search)
    return _to_summaries(_summaries(query, sort, order).all())


def _count_by_status(visible: Query[Clubs]) -> dict[ClubStatus, int]:
    rows = (
        visible.with_entities(Clubs.status, func.count()).group_by(Clubs.status).all()
    )
    counts = {status: count for status, count in rows}
    return {status: counts.get(status, 0) for status in ClubStatus}


def _ordered(
    query: Query[Clubs], sort: ClubSortField | None, order: SortOrder
) -> Query[Clubs]:
    """Creation order unless a column is chosen. id breaks ties in the same
    direction, so asc and desc are exact reverses and paging is stable."""
    if sort is None:
        return query.order_by(Clubs.id.asc())
    if order == SortOrder.asc:
        return query.order_by(_SORT_COLUMNS[sort].asc(), Clubs.id.asc())
    return query.order_by(_SORT_COLUMNS[sort].desc(), Clubs.id.desc())


def get_club(db: Session, club_id: int) -> Clubs:
    club = db.query(Clubs).filter(Clubs.id == club_id).first()
    if not club:
        raise NotFound("Club not found")
    return club


def get_club_for_update(db: Session, club_id: int) -> Clubs:
    """Locks the club row until commit; every write to a club or its
    requirements starts here, so writes to one club run one at a time.
    populate_existing() replaces any stale copy this session already holds."""
    club = (
        db.query(Clubs)
        .filter(Clubs.id == club_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not club:
        raise NotFound("Club not found")
    return club


def ensure_owner_or_admin(club: Clubs, user: User) -> None:
    if user.role != UserRole.admin and club.submitter_id != user.id:
        raise Forbidden("Not your club")


def ensure_owner(club: Clubs, user: User) -> None:
    """For changes to a club's content: admins review clubs but never edit them."""
    if club.submitter_id != user.id:
        raise Forbidden("Not your club")


def get_club_for_user(db: Session, club_id: int, user: User) -> Clubs:
    """Existence before ownership, so a missing club is a 404 for everyone."""
    club = get_club(db, club_id)
    ensure_owner_or_admin(club, user)
    return club


def update_club_for_user(
    db: Session,
    club_id: int,
    user: User,
    name: str | None,
    description: str | None,
) -> Clubs:
    """Ownership before status, so a stranger never learns a club's state."""
    club = get_club_for_update(db, club_id)
    ensure_owner(club, user)

    if club.status not in EDITABLE_STATUSES:
        raise Conflict("Cannot edit a club that has already been submitted")

    if name is not None:
        club.name = name
    if description is not None:
        club.description = description

    db.commit()
    db.refresh(club)
    return club


def submit_club_for_user(db: Session, club_id: int, user: User) -> Clubs:
    club = get_club_for_update(db, club_id)
    ensure_owner(club, user)
    return attempt_transition(db, club, ClubStatus.submitted, user)


def resubmit_club_for_user(db: Session, club_id: int, user: User) -> Clubs:
    club = get_club_for_update(db, club_id)
    ensure_owner(club, user)
    if club.status != ClubStatus.changes_requested:
        raise Conflict(f"Cannot resubmit a club in status {club.status.value}")
    return attempt_transition(db, club, ClubStatus.submitted, user)


def review_club(
    db: Session,
    club_id: int,
    to_status: ClubStatus,
    admin: User,
    note: str | None = None,
) -> Clubs:
    """Admin-side transition (start-review / request-changes / approve / reject)."""
    club = get_club_for_update(db, club_id)
    return attempt_transition(db, club, to_status, admin, note)


def list_club_events(db: Session, club_id: int) -> list[tuple[Event, str]]:
    """The club's registration history, newest first, with the actor's name;
    served by idx_events_club_time. Comments and requests have their own."""
    return (
        db.query(Event, User.name)
        .join(User, User.id == Event.actor_id)
        .filter(
            Event.club_id == club_id,
            Event.event_type != EventType.comment_posted,
            Event.request_id.is_(None),
        )
        .order_by(Event.created_at.desc(), Event.id.desc())
        .tuples()
        .all()
    )


def list_requirements(db: Session, club_id: int) -> list[Requirement]:
    return (
        db.query(Requirement)
        .filter(Requirement.club_id == club_id)
        .order_by(Requirement.id.asc())
        .all()
    )
