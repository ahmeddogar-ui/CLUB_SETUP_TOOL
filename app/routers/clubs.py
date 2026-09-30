from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user, require_role
from app.database import DbSession
from app.models import (
    ClubEvent,
    Clubs,
    ClubStatus,
    Requirement,
    RequirementKind,
    RequirementStatus,
    RequirementType,
    User,
    UserRole,
)
from app.schemas import ClubCreateRequest, ClubOut, ClubUpdateRequest, NoteRequest
from app.transitions import InvalidTransition, TransitionBlocked, attempt_transition

router = APIRouter(prefix="/clubs", tags=["clubs"])

INITIAL_REQUIREMENTS = (
    (RequirementType.constitution, RequirementKind.document),
    (RequirementType.exec_list, RequirementKind.document),
    (RequirementType.budget, RequirementKind.document),
    (RequirementType.advisor_form, RequirementKind.document),
    (RequirementType.bank_account_setup, RequirementKind.checklist),
    (RequirementType.exec_onboarding, RequirementKind.checklist),
)

EDITABLE_STATUSES = (ClubStatus.drafting, ClubStatus.changes_requested)


@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
def create_club(
    payload: ClubCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = Clubs(
        name=payload.name,
        description=payload.description,
        submitter_id=current_user.id,
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
        ClubEvent(
            club_id=club.id,
            actor_id=current_user.id,
            event_type="created",
            from_status=None,
            to_status=ClubStatus.drafting,
        )
    )

    db.commit()
    db.refresh(club)
    return club


class ClubSort(str, Enum):
    oldest = "oldest"
    newest = "newest"


@router.get("", response_model=list[ClubOut])
def list_clubs(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    status_filter: list[ClubStatus] | None = Query(default=None, alias="status"),
    sort: ClubSort | None = None,
):
    query = db.query(Clubs)

    # Role scoping first; the filters below only ever narrow this set.
    if current_user.role != UserRole.admin:
        query = query.filter(Clubs.submitter_id == current_user.id)

    if status_filter:
        query = query.filter(Clubs.status.in_(status_filter))

    if sort == ClubSort.oldest:
        # Longest-waiting first; id breaks ties between identical timestamps.
        query = query.order_by(Clubs.updated_at.asc(), Clubs.id.asc())
    elif sort == ClubSort.newest:
        # Most recently changed first; the exact reverse of oldest.
        query = query.order_by(Clubs.updated_at.desc(), Clubs.id.desc())
    else:
        query = query.order_by(Clubs.id.asc())

    return query.all()


@router.get("/{club_id}", response_model=ClubOut)
def get_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = db.query(Clubs).filter(Clubs.id == club_id).first()

    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        )

    if current_user.role != UserRole.admin and club.submitter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your club"
        )

    return club


@router.patch("/{club_id}", response_model=ClubOut)
def update_club(
    club_id: int,
    payload: ClubUpdateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = db.query(Clubs).filter(Clubs.id == club_id).first()

    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        )

    if current_user.role != UserRole.admin and club.submitter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your club"
        )

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


def get_club_or_404(db: DbSession, club_id: int) -> Clubs:
    club = db.query(Clubs).filter(Clubs.id == club_id).first()
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        )
    return club


def ensure_owner_or_admin(club: Clubs, current_user: User) -> None:
    if current_user.role != UserRole.admin and club.submitter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your club"
        )


def _transition(
    db: DbSession,
    club: Clubs,
    to_status: ClubStatus,
    actor: User,
    note: str | None = None,
) -> Clubs:
    try:
        return attempt_transition(db, club, to_status, actor, note)
    except (InvalidTransition, TransitionBlocked) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{club_id}/submit", response_model=ClubOut)
def submit_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_or_404(db, club_id)
    ensure_owner_or_admin(club, current_user)
    return _transition(db, club, ClubStatus.submitted, current_user)


@router.post("/{club_id}/resubmit", response_model=ClubOut)
def resubmit_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_or_404(db, club_id)
    ensure_owner_or_admin(club, current_user)
    if club.status != ClubStatus.changes_requested:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot resubmit a club in status {club.status.value}",
        )
    return _transition(db, club, ClubStatus.submitted, current_user)


@router.post("/{club_id}/start-review", response_model=ClubOut)
def start_review(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    club = get_club_or_404(db, club_id)
    return _transition(db, club, ClubStatus.under_review, current_user)


@router.post("/{club_id}/request-changes", response_model=ClubOut)
def request_changes(
    club_id: int,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    club = get_club_or_404(db, club_id)
    return _transition(
        db, club, ClubStatus.changes_requested, current_user, payload.note
    )


@router.post("/{club_id}/approve", response_model=ClubOut)
def approve_club(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    club = get_club_or_404(db, club_id)
    return _transition(db, club, ClubStatus.approved, current_user)


@router.post("/{club_id}/reject", response_model=ClubOut)
def reject_club(
    club_id: int,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    club = get_club_or_404(db, club_id)
    return _transition(db, club, ClubStatus.rejected, current_user, payload.note)
