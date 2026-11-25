"""Demo data for trying the app: an admin, a club lead, and the lead's clubs in
three different states. Built through the services, so every club has the
same history a real one would. Each service call commits on its own, so a run
that fails partway leaves partial data: reseed into a fresh database."""

from sqlalchemy.orm import Session

from app.models import ClubStatus, RequirementKind, RequirementType, User
from app.services.auth import make_admin, normalize_email, register_user
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

_DOCUMENT_TYPES = [
    requirement_type
    for requirement_type, kind in INITIAL_REQUIREMENTS
    if kind == RequirementKind.document
]


def demo_data_exists(db: Session) -> bool:
    emails = [normalize_email(DEMO_ADMIN_EMAIL), normalize_email(DEMO_LEAD_EMAIL)]
    return db.query(User).filter(User.email.in_(emails)).first() is not None


def seed_demo(db: Session) -> None:
    admin = register_user(db, "Demo Admin", DEMO_ADMIN_EMAIL, DEMO_PASSWORD)
    # Updates this same User object, so `admin` is an admin from here on.
    make_admin(db, DEMO_ADMIN_EMAIL)
    lead = register_user(db, "Demo Lead", DEMO_LEAD_EMAIL, DEMO_PASSWORD)

    create_club_for_user(
        db, lead, "Chess Club", "Weekly casual and rated games for all levels."
    )

    film = _create_club_with_documents(
        db, lead, "Film Society", "Screenings and discussion every Thursday."
    )
    submit_club_for_user(db, film, lead)

    robotics = _create_club_with_documents(
        db, lead, "Robotics Club", "Building robots for the regional competition."
    )
    submit_club_for_user(db, robotics, lead)
    review_club(db, robotics, ClubStatus.under_review, admin)
    for requirement_type, _ in INITIAL_REQUIREMENTS:
        approve_requirement(db, robotics, requirement_type, admin)
    review_club(db, robotics, ClubStatus.approved, admin)


def _create_club_with_documents(
    db: Session, lead: User, name: str, description: str
) -> int:
    """Returns the new club's id, with every document link provided."""
    club = create_club_for_user(db, lead, name, description)
    for requirement_type in _DOCUMENT_TYPES:
        set_requirement_link(
            db, club.id, requirement_type, _demo_link(requirement_type), lead
        )
    return club.id


def _demo_link(requirement_type: RequirementType) -> str:
    return f"https://example.com/demo/{requirement_type.value}"
