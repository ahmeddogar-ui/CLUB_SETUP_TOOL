from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.security import require_role
from app.database import DbSession
from app.models import EventType, User, UserRole
from app.schemas import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX, ActivityOut, Page
from app.services.activity import ActivityEntry, ActivityFilters, list_activity

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=Page[ActivityOut])
def get_activity(
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
    actor_id: int | None = None,
    club_id: int | None = None,
    event_type: EventType | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    offset: int = Query(default=0, ge=0),
):
    filters = ActivityFilters(actor_id, club_id, event_type, since, until)
    page = list_activity(db, filters, limit, offset)
    return Page(items=[_activity_out(entry) for entry in page.items], total=page.total)


def _activity_out(entry: ActivityEntry) -> ActivityOut:
    event = entry.event
    return ActivityOut(
        id=event.id,
        event_type=EventType(event.event_type),
        created_at=event.created_at,
        actor_id=event.actor_id,
        actor_name=entry.actor_name,
        club_id=event.club_id,
        club_name=entry.club_name,
        subject_user_id=event.subject_user_id,
        subject_user_name=entry.subject_user_name,
        request_id=event.request_id,
        request_title=entry.request_title,
        requirement_type=entry.requirement_type,
        from_status=event.from_status,
        to_status=event.to_status,
        note=event.note,
    )
