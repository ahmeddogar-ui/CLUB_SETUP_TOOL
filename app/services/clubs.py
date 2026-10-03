from enum import Enum

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
    UserRole,
)
from app.transitions import InvalidTransition, TransitionBlocked, attempt_transition

EDITABLE_STATUSES = (ClubStatus.drafting, ClubStatus.changes_requested)

INITIAL_REQUIREMENTS = (
    (RequirementType.constitution, RequirementKind.document),
    (RequirementType.exec_list, RequirementKind.document),
    (RequirementType.budget, RequirementKind.document),
    (RequirementType.advisor_form, RequirementKind.document),
    (RequirementType.bank_account_setup, RequirementKind.checklist),
    (RequirementType.exec_onboarding, RequirementKind.checklist),
)


class ClubSort(str, Enum):
    oldest = "oldest"
    newest = "newest"


def create_club_for_user(db: Session, user: User, name: str, description: str) -> Clubs:
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
        ClubEvent(
            club_id=club.id,
            actor_id=user.id,
            event_type="created",
            from_status=None,
            to_status=ClubStatus.drafting,
        )
    )

    db.commit()
    db.refresh(club)
    return club


def list_clubs_for_user(
    db: Session,
    user: User,
    statuses: list[ClubStatus] | None = None,
    sort: ClubSort | None = None,
) -> list[Clubs]:
    query = db.query(Clubs)

    # Role scoping first; the filters below only ever narrow this set.
    if user.role != UserRole.admin:
        query = query.filter(Clubs.submitter_id == user.id)

    if statuses:
        query = query.filter(Clubs.status.in_(statuses))

    if sort == ClubSort.oldest:
        # Longest-waiting first; id breaks ties between identical timestamps.
        query = query.order_by(Clubs.updated_at.asc(), Clubs.id.asc())
    elif sort == ClubSort.newest:
        # Most recently changed first; the exact reverse of oldest.
        query = query.order_by(Clubs.updated_at.desc(), Clubs.id.desc())
    else:
        query = query.order_by(Clubs.id.asc())

    return query.all()


def get_club_or_404(db: Session, club_id: int) -> Clubs:
    club = db.query(Clubs).filter(Clubs.id == club_id).first()
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        )
    return club


def ensure_owner_or_admin(club: Clubs, user: User) -> None:
    if user.role != UserRole.admin and club.submitter_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your club"
        )


def get_club_for_user(db: Session, club_id: int, user: User) -> Clubs:
    """Existence before ownership, so a missing club is a 404 for everyone."""
    club = get_club_or_404(db, club_id)
    ensure_owner_or_admin(club, user)
    return club


def transition_club(
    db: Session,
    club: Clubs,
    to_status: ClubStatus,
    actor: User,
    note: str | None = None,
) -> Clubs:
    try:
        return attempt_transition(db, club, to_status, actor, note)
    except (InvalidTransition, TransitionBlocked) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


def submit_club_for_user(db: Session, club_id: int, user: User) -> Clubs:
    club = get_club_for_user(db, club_id, user)
    return transition_club(db, club, ClubStatus.submitted, user)


def resubmit_club_for_user(db: Session, club_id: int, user: User) -> Clubs:
    club = get_club_for_user(db, club_id, user)
    if club.status != ClubStatus.changes_requested:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot resubmit a club in status {club.status.value}",
        )
    return transition_club(db, club, ClubStatus.submitted, user)


def review_club(
    db: Session, club_id: int, to_status: ClubStatus, admin: User, note: str | None = None
) -> Clubs:
    """Admin-side transition (start-review / request-changes / approve / reject)."""
    club = get_club_or_404(db, club_id)
    return transition_club(db, club, to_status, admin, note)


def list_club_events(db: Session, club_id: int) -> list[tuple[ClubEvent, str]]:
    """Newest first, with the actor's name; served by idx_events_club_time."""
    return (
        db.query(ClubEvent, User.name)
        .join(User, User.id == ClubEvent.actor_id)
        .filter(ClubEvent.club_id == club_id)
        .order_by(ClubEvent.created_at.desc(), ClubEvent.id.desc())
        .all()
    )


def list_requirements(db: Session, club_id: int) -> list[Requirement]:
    return (
        db.query(Requirement)
        .filter(Requirement.club_id == club_id)
        .order_by(Requirement.id.asc())
        .all()
    )
