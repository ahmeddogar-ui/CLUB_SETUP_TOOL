from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
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
from app.schemas import ClubCreateRequest, ClubOut, ClubUpdateRequest

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
