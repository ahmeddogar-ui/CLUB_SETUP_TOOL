from fastapi import APIRouter, Depends, HTTPException, status

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
from app.routers.clubs import (
    EDITABLE_STATUSES,
    ensure_owner_or_admin,
    get_club_or_404,
)
from app.schemas import (
    NoteRequest,
    OptionalNoteRequest,
    RequirementLinkRequest,
    RequirementOut,
)

router = APIRouter(prefix="/clubs", tags=["requirements"])


def _get_requirement_or_404(
    db: DbSession, club_id: int, requirement_type: RequirementType
) -> Requirement:
    # Filter on both columns so a type can only ever resolve to this club's own row.
    requirement = (
        db.query(Requirement)
        .filter(
            Requirement.club_id == club_id,
            Requirement.requirement_type == requirement_type,
        )
        .first()
    )
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found"
        )
    return requirement


def _get_reviewable_requirement(
    db: DbSession, club_id: int, requirement_type: RequirementType
) -> tuple[Clubs, Requirement]:
    club = get_club_or_404(db, club_id)
    if club.status != ClubStatus.under_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirements can only be reviewed while the club is under_review",
        )
    return club, _get_requirement_or_404(db, club_id, requirement_type)


def _record_requirement_event(
    db: DbSession,
    club: Clubs,
    requirement: Requirement,
    event_type: str,
    actor: User,
    note: str | None = None,
    link_url: str | None = None,
) -> None:
    # The club's status doesn't move on a requirement action, so from == to.
    # Added to the same session as the requirement change, so one commit saves both.
    db.add(
        ClubEvent(
            club_id=club.id,
            actor_id=actor.id,
            event_type=event_type,
            requirement_id=requirement.id,
            from_status=club.status,
            to_status=club.status,
            note=note,
            link_url=link_url,
        )
    )


@router.put(
    "/{club_id}/requirements/{requirement_type}/link",
    response_model=RequirementOut,
)
def set_requirement_link(
    club_id: int,
    requirement_type: RequirementType,
    payload: RequirementLinkRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    club = get_club_or_404(db, club_id)
    ensure_owner_or_admin(club, current_user)

    if club.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change documents on a club that has already been submitted",
        )

    requirement = _get_requirement_or_404(db, club_id, requirement_type)

    if requirement.kind != RequirementKind.document:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{requirement_type.value} is a checklist item and has no link",
        )

    requirement.link_url = str(payload.link_url)
    requirement.status = RequirementStatus.submitted
    requirement.reviewer_note = None
    _record_requirement_event(
        db,
        club,
        requirement,
        "requirement_submitted",
        current_user,
        link_url=requirement.link_url,
    )

    db.commit()
    db.refresh(requirement)
    return requirement


@router.post(
    "/{club_id}/requirements/{requirement_type}/approve",
    response_model=RequirementOut,
)
def approve_requirement(
    club_id: int,
    requirement_type: RequirementType,
    db: DbSession,
    payload: OptionalNoteRequest | None = None,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    club, requirement = _get_reviewable_requirement(db, club_id, requirement_type)

    if requirement.status == RequirementStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{requirement_type.value} is already approved",
        )

    if (
        requirement.kind == RequirementKind.document
        and requirement.status != RequirementStatus.submitted
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{requirement_type.value} has no newly provided document to approve",
        )

    note = payload.note if payload else None
    requirement.status = RequirementStatus.approved
    requirement.reviewer_note = note.strip() if note and note.strip() else None
    _record_requirement_event(
        db, club, requirement, "requirement_approved", current_user, note=requirement.reviewer_note
    )

    db.commit()
    db.refresh(requirement)
    return requirement


@router.post(
    "/{club_id}/requirements/{requirement_type}/reject",
    response_model=RequirementOut,
)
def reject_requirement(
    club_id: int,
    requirement_type: RequirementType,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    club, requirement = _get_reviewable_requirement(db, club_id, requirement_type)

    requirement.status = RequirementStatus.rejected
    requirement.reviewer_note = payload.note
    _record_requirement_event(
        db, club, requirement, "requirement_rejected", current_user, note=payload.note
    )

    db.commit()
    db.refresh(requirement)
    return requirement
