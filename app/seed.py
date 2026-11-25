"""Demo data for trying the app: an admin, a club lead, and the lead's clubs in
three different states. Built through the services, so every club has the
same history a real one would."""

from sqlalchemy.orm import Session

from app.models import ClubStatus, RequirementKind, RequirementType, User
from app.services.auth import make_admin, register_user
from app.services.clubs import (
    INITIAL_REQUIREMENTS,
    create_club_for_user,
    review_club,
    submit_club_for_user,
)
from app.services.requirements import approve_requirement, set_requirement_link

DEMO_ADMIN_EMAIL = "demo-admin@example.com"
DEMO_LEAD_EMAIL = "demo-lead@example.com"
# Printed by the CLI and listed in the README: demo accounts only.
DEMO_PASSWORD = "demo-password"

DOCUMENT_TYPES = [
    requirement_type
    for requirement_type, kind in INITIAL_REQUIREMENTS
    if kind == RequirementKind.document
]


def seed_demo(db: Session) -> None:
    """Raises Conflict if the demo accounts already exist."""
    admin = register_user(db, "Demo Admin", DEMO_ADMIN_EMAIL, DEMO_PASSWORD)
    make_admin(db, DEMO_ADMIN_EMAIL)
    lead = register_user(db, "Demo Lead", DEMO_LEAD_EMAIL, DEMO_PASSWORD)

    create_club_for_user(
        db, lead, "Chess Club", "Weekly casual and rated games for all levels."
    )

    film = _club_with_documents(
        db, lead, "Film Society", "Screenings and discussion every Thursday."
    )
    submit_club_for_user(db, film, lead)

    robotics = _club_with_documents(
        db, lead, "Robotics Club", "Building robots for the regional competition."
    )
    submit_club_for_user(db, robotics, lead)
    review_club(db, robotics, ClubStatus.under_review, admin)
    for requirement_type, _ in INITIAL_REQUIREMENTS:
        approve_requirement(db, robotics, requirement_type, admin)
    review_club(db, robotics, ClubStatus.approved, admin)


def _club_with_documents(db: Session, lead: User, name: str, description: str) -> int:
    club = create_club_for_user(db, lead, name, description)
    for requirement_type in DOCUMENT_TYPES:
        set_requirement_link(
            db, club.id, requirement_type, _demo_link(requirement_type), lead
        )
    return club.id


def _demo_link(requirement_type: RequirementType) -> str:
    return f"https://example.com/demo/{requirement_type.value}"
