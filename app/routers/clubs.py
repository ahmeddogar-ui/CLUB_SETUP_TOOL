from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user, require_role
from app.database import DbSession
from app.models import (
    Clubs,
    ClubStatus,
    User,
    UserRole,
)
from app.schemas import ClubCreateRequest, ClubOut, ClubUpdateRequest, NoteRequest
from app.services.clubs import (  # noqa: F401  (INITIAL_REQUIREMENTS re-exported for tests)
    EDITABLE_STATUSES,
    INITIAL_REQUIREMENTS,
    ClubSort,
    create_club_for_user,
    get_club_for_user,
    list_clubs_for_user,
    resubmit_club_for_user,
    review_club,
    submit_club_for_user,
)

router = APIRouter(prefix="/clubs", tags=["clubs"])

@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
def create_club(
    payload: ClubCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return create_club_for_user(db, current_user, payload.name, payload.description)


@router.get("", response_model=list[ClubOut])
def list_clubs(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    status_filter: list[ClubStatus] | None = Query(default=None, alias="status"),
    sort: ClubSort | None = None,
):
    return list_clubs_for_user(db, current_user, status_filter, sort)


@router.get("/{club_id}", response_model=ClubOut)
def get_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_for_user(db, club_id, current_user)

    return club


@router.patch("/{club_id}", response_model=ClubOut)
def update_club(
    club_id: int,
    payload: ClubUpdateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_for_user(db, club_id, current_user)

    if club.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit a club that has already been submitted",
        )

    if payload.name is not None:
        club.name = payload.name
    if payload.description is not None:
        club.description = payload.description

    db.commit()
    db.refresh(club)
    return club


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
    return review_club(db, club_id, ClubStatus.changes_requested, current_user, payload.note)


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
