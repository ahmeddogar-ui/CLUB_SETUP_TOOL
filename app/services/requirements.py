from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    ClubEvent,
    Clubs,
    ClubStatus,
    Requirement,
    RequirementKind,
    RequirementStatus,
    RequirementType,
    User,
)
from app.services.clubs import EDITABLE_STATUSES, ensure_owner_or_admin, get_club_or_404


def get_requirement_or_404(
    db: Session, club_id: int, requirement_type: RequirementType
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
    db: Session, club_id: int, requirement_type: RequirementType
) -> tuple[Clubs, Requirement]:
    club = get_club_or_404(db, club_id)
    if club.status != ClubStatus.under_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirements can only be reviewed while the club is under_review",
        )
    return club, get_requirement_or_404(db, club_id, requirement_type)


def _record_requirement_event(
    db: Session,
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


def set_requirement_link(
    db: Session,
    club_id: int,
    requirement_type: RequirementType,
    link_url: str,
    user: User,
) -> Requirement:
    club = get_club_or_404(db, club_id)
    ensure_owner_or_admin(club, user)

    if club.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change documents on a club that has already been submitted",
        )

    requirement = get_requirement_or_404(db, club_id, requirement_type)

    if requirement.kind != RequirementKind.document:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{requirement_type.value} is a checklist item and has no link",
        )

    requirement.link_url = link_url
    requirement.status = RequirementStatus.submitted
    requirement.reviewer_note = None
    _record_requirement_event(
        db,
        club,
        requirement,
        "requirement_submitted",
        user,
        link_url=requirement.link_url,
    )

    db.commit()
    db.refresh(requirement)
    return requirement


def approve_requirement(
    db: Session,
    club_id: int,
    requirement_type: RequirementType,
    admin: User,
    note: str | None = None,
) -> Requirement:
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

    requirement.status = RequirementStatus.approved
    requirement.reviewer_note = note.strip() if note and note.strip() else None
    _record_requirement_event(
        db, club, requirement, "requirement_approved", admin, note=requirement.reviewer_note
    )

    db.commit()
    db.refresh(requirement)
    return requirement


def reject_requirement(
    db: Session,
    club_id: int,
    requirement_type: RequirementType,
    admin: User,
    note: str,
) -> Requirement:
    club, requirement = _get_reviewable_requirement(db, club_id, requirement_type)

    requirement.status = RequirementStatus.rejected
    requirement.reviewer_note = note
    _record_requirement_event(
        db, club, requirement, "requirement_rejected", admin, note=note
    )

    db.commit()
    db.refresh(requirement)
    return requirement
