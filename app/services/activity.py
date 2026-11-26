"""The admin's activity log: every event in the app, newest first."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session, aliased

from app.listing import Page, paginate
from app.models import Clubs, Event, EventType, Requirement, RequirementType, User


@dataclass(frozen=True)
class ActivityFilters:
    actor_id: int | None = None
    club_id: int | None = None
    event_type: EventType | None = None
    # Inclusive start, exclusive end.
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True)
class ActivityEntry:
    event: Event
    actor_name: str
    club_name: str | None
    subject_user_name: str | None
    requirement_type: RequirementType | None


def list_activity(
    db: Session, filters: ActivityFilters, limit: int, offset: int
) -> Page[ActivityEntry]:
    """One query for the page: names come from joins, not per-row lookups."""
    actor = aliased(User)
    subject = aliased(User)
    query = (
        db.query(
            Event, actor.name, Clubs.name, subject.name, Requirement.requirement_type
        )
        .join(actor, actor.id == Event.actor_id)
        .outerjoin(Clubs, Clubs.id == Event.club_id)
        .outerjoin(subject, subject.id == Event.subject_user_id)
        .outerjoin(Requirement, Requirement.id == Event.requirement_id)
    )
    if filters.actor_id is not None:
        query = query.filter(Event.actor_id == filters.actor_id)
    if filters.club_id is not None:
        query = query.filter(Event.club_id == filters.club_id)
    if filters.event_type is not None:
        query = query.filter(Event.event_type == filters.event_type)
    if filters.since is not None:
        query = query.filter(Event.created_at >= filters.since)
    if filters.until is not None:
        query = query.filter(Event.created_at < filters.until)

    page = paginate(
        query.order_by(Event.created_at.desc(), Event.id.desc()), limit, offset
    )
    return Page(
        items=[ActivityEntry(*row) for row in page.items],
        total=page.total,
    )
