from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    ClubEvent,
    Clubs,
    ClubStatus,
    Requirement,
    RequirementKind,
    RequirementStatus,
    User,
)


ALLOWED: dict[tuple[str, str], str] = {
    ("drafting", "submitted"): "club_lead",
    ("submitted", "under_review"): "admin",
    ("under_review", "changes_requested"): "admin",
    ("under_review", "approved"): "admin",
    ("under_review", "rejected"): "admin",
    ("changes_requested", "submitted"): "club_lead",
}

EVENT_TYPES: dict[tuple[str, str], str] = {
    ("drafting", "submitted"): "submitted",
    ("submitted", "under_review"): "review_started",
    ("under_review", "changes_requested"): "changes_requested",
    ("under_review", "approved"): "approved",
    ("under_review", "rejected"): "rejected",
    ("changes_requested", "submitted"): "resubmitted",
}


class InvalidTransition(Exception):
    pass


class TransitionBlocked(Exception):
    pass


def _event_for(from_status: str, to_status: str) -> str:
    return EVENT_TYPES[(from_status, to_status)]


def _check_guards(db: Session, club: Clubs, to_status: str, note: str | None) -> None:
    key = (club.status, to_status)

    requirements = (db.query(Requirement).filter(Requirement.club_id == club.id).all())

    if key in (
        (ClubStatus.drafting, ClubStatus.submitted),
        (ClubStatus.changes_requested, ClubStatus.submitted),
    ):
        missing = [
            field
            for field in ("name", "description")
            if not (getattr(club, field) or "").strip()
        ]
        missing += [
            requirement.requirement_type.value
            for requirement in requirements
            if requirement.kind == RequirementKind.document
            and requirement.status
            in (RequirementStatus.pending, RequirementStatus.rejected)
        ]

        if missing:
            raise TransitionBlocked(f"missing: {', '.join(missing)}")

    elif key == (ClubStatus.under_review, ClubStatus.approved):

        not_approved = [
            requirement.requirement_type.value
            for requirement in requirements
            if requirement.status != RequirementStatus.approved
        ]

        if not_approved:
            raise TransitionBlocked(
                f"requirements not all approved: {', '.join(not_approved)}"
            )

    elif key in (
        (ClubStatus.under_review, ClubStatus.changes_requested),
        (ClubStatus.under_review, ClubStatus.rejected),
    ):
        if not note or not note.strip():
            raise TransitionBlocked("a note is required for this action")


def attempt_transition(
    db: Session,
    club: Clubs,
    to_status: str,
    actor: User,
    note: str | None = None,
) -> Clubs:
    
    key = (club.status, to_status)

    if key not in ALLOWED:
        raise InvalidTransition(f"Cannot move {club.status} -> {to_status}")

    if actor.role != ALLOWED[key]:
        raise InvalidTransition(f"{actor.role} may not perform this transition")

    _check_guards(db, club, to_status, note)

    from_status = club.status
    club.status = to_status
    club.updated_at = datetime.now(timezone.utc)

    db.add(
        ClubEvent(
            club_id=club.id,
            actor_id=actor.id,
            event_type=_event_for(from_status, to_status),
            from_status=from_status,
            to_status=to_status,
            note=note.strip() if note and note.strip() else None,
        )
    )

    # Status change and event row go out in one commit; if either write fails,
    # roll both back so the club's status and its history can never disagree.
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(club)
    return club
