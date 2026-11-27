"""A club's discussion: comments are events (comment_posted) with the body as
the note, so they share the append-only history and the activity log."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.listing import Page, paginate
from app.models import Event, EventType, User, UserRole
from app.services.clubs import get_club_for_user


@dataclass(frozen=True)
class Comment:
    id: int
    body: str
    author_name: str
    author_role: UserRole
    created_at: datetime


def list_comments(
    db: Session, club_id: int, user: User, limit: int, offset: int
) -> Page[Comment]:
    """Newest first; served by idx_events_club_time."""
    club = get_club_for_user(db, club_id, user)
    query = (
        db.query(Event, User.name, User.role)
        .join(User, User.id == Event.actor_id)
        .filter(Event.club_id == club.id, Event.event_type == EventType.comment_posted)
        .order_by(Event.created_at.desc(), Event.id.desc())
    )
    page = paginate(query, limit, offset)
    return Page(
        items=[_comment(event, name, role) for event, name, role in page.items],
        total=page.total,
    )


def post_comment(db: Session, club_id: int, user: User, body: str) -> Comment:
    """Anyone who can see the club can post. No row lock: a comment only adds
    a row and changes nothing a concurrent request could also change."""
    club = get_club_for_user(db, club_id, user)
    event = Event(
        club_id=club.id,
        actor_id=user.id,
        event_type=EventType.comment_posted,
        note=body,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _comment(event, user.name, user.role)


def _comment(event: Event, author_name: str, author_role: UserRole) -> Comment:
    # A comment_posted event always has a body.
    assert event.note is not None
    return Comment(event.id, event.note, author_name, author_role, event.created_at)
