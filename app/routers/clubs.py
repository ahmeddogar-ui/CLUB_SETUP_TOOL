import csv
import io

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security import get_current_user, require_role
from app.database import DbSession
from app.models import (
    ClubStatus,
    User,
    UserRole,
)
from app.schemas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    SEARCH_MAX_LENGTH,
    ClubCreateRequest,
    ClubEventOut,
    ClubListItemOut,
    ClubOut,
    ClubPageOut,
    ClubUpdateRequest,
    NoteRequest,
)
from app.services.clubs import (
    ClubSortField,
    ClubSummary,
    SortOrder,
    create_club_for_user,
    export_clubs,
    get_club_for_user,
    list_club_events,
    list_clubs_for_user,
    resubmit_club_for_user,
    review_club,
    submit_club_for_user,
    update_club_for_user,
)

router = APIRouter(prefix="/clubs", tags=["clubs"])

EXPORT_HEADER = (
    "id",
    "name",
    "status",
    "owner",
    "documents_provided",
    "documents_total",
    "updated_at",
)
# Spreadsheets run a cell starting with one of these as a formula.
FORMULA_TRIGGER_CHARACTERS = ("=", "+", "-", "@", "\t", "\r")


@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
def create_club(
    payload: ClubCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return create_club_for_user(db, current_user, payload.name, payload.description)


@router.get("", response_model=ClubPageOut)
def list_clubs(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    status_filter: list[ClubStatus] | None = Query(default=None, alias="status"),
    sort: ClubSortField | None = None,
    order: SortOrder = SortOrder.asc,
    q: str | None = Query(default=None, max_length=SEARCH_MAX_LENGTH),
    limit: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    offset: int = Query(default=0, ge=0),
):
    page = list_clubs_for_user(
        db,
        current_user,
        statuses=status_filter,
        sort=sort,
        order=order,
        search=q,
        limit=limit,
        offset=offset,
    )
    return ClubPageOut(
        items=[_list_item(summary) for summary in page.items],
        total=page.total,
        status_counts=page.status_counts,
    )


def _list_item(summary: ClubSummary) -> ClubListItemOut:
    club = summary.club
    return ClubListItemOut(
        id=club.id,
        name=club.name,
        description=club.description,
        status=club.status.value,
        submitter_id=club.submitter_id,
        updated_at=club.updated_at,
        owner_name=summary.owner_name,
        documents_provided=summary.documents_provided,
        documents_total=summary.documents_total,
    )


@router.get("/export.csv")
def export_clubs_csv(
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
    status_filter: list[ClubStatus] | None = Query(default=None, alias="status"),
    sort: ClubSortField | None = None,
    order: SortOrder = SortOrder.asc,
    q: str | None = Query(default=None, max_length=SEARCH_MAX_LENGTH),
):
    summaries = export_clubs(
        db, current_user, statuses=status_filter, sort=sort, order=order, search=q
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_HEADER)
    for summary in summaries:
        club = summary.club
        writer.writerow(
            [
                club.id,
                _neutralize_formula(club.name),
                club.status.value,
                _neutralize_formula(summary.owner_name),
                summary.documents_provided,
                summary.documents_total,
                club.updated_at.isoformat(),
            ]
        )
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="clubs.csv"'},
    )


def _neutralize_formula(text: str) -> str:
    """Prefix a quote so a spreadsheet shows the text instead of running it."""
    if text.startswith(FORMULA_TRIGGER_CHARACTERS):
        return f"'{text}"
    return text


@router.get("/{club_id}", response_model=ClubOut)
def get_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_for_user(db, club_id, current_user)

    return club


@router.get("/{club_id}/events", response_model=list[ClubEventOut])
def get_club_events(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_for_user(db, club_id, current_user)
    return [
        ClubEventOut(
            id=event.id,
            event_type=event.event_type,
            requirement_id=event.requirement_id,
            link_url=event.link_url,
            from_status=event.from_status,
            to_status=event.to_status,
            note=event.note,
            actor_name=actor_name,
            created_at=event.created_at,
        )
        for event, actor_name in list_club_events(db, club.id)
    ]


@router.patch("/{club_id}", response_model=ClubOut)
def update_club(
    club_id: int,
    payload: ClubUpdateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return update_club_for_user(
        db, club_id, current_user, payload.name, payload.description
    )


@router.post("/{club_id}/submit", response_model=ClubOut)
def submit_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return submit_club_for_user(db, club_id, current_user)


@router.post("/{club_id}/resubmit", response_model=ClubOut)
def resubmit_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return resubmit_club_for_user(db, club_id, current_user)


@router.post("/{club_id}/start-review", response_model=ClubOut)
def start_review(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return review_club(db, club_id, ClubStatus.under_review, current_user)


@router.post("/{club_id}/request-changes", response_model=ClubOut)
def request_changes(
    club_id: int,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return review_club(
        db, club_id, ClubStatus.changes_requested, current_user, payload.note
    )


@router.post("/{club_id}/approve", response_model=ClubOut)
def approve_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return review_club(db, club_id, ClubStatus.approved, current_user)


@router.post("/{club_id}/reject", response_model=ClubOut)
def reject_club(
    club_id: int,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return review_club(db, club_id, ClubStatus.rejected, current_user, payload.note)
