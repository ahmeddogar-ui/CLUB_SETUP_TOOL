"""Demo data for trying the app: an admin, four club leads, and sixteen clubs
spread over every status. Built through the services, so every club has the
same requirements and history a real one would. Each service call commits on
its own, so a run that fails partway leaves partial data: reseed into a fresh
database."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Clubs,
    ClubStatus,
    RequirementKind,
    RequirementType,
    User,
)
from app.services.auth import make_admin, normalize_email, register_user
from app.services.clubs import (
    INITIAL_REQUIREMENTS,
    create_club_for_user,
    review_club,
    submit_club_for_user,
)
from app.services.requirements import (
    approve_requirement,
    reject_requirement,
    set_requirement_link,
)

DEMO_ADMIN_EMAIL = "demo-admin@example.com"
DEMO_LEAD_EMAIL = "demo-lead@example.com"
# Printed by the CLI and listed in the README: demo accounts only.
DEMO_PASSWORD = "demo-password"

DEMO_LEADS = [
    ("Demo Lead", DEMO_LEAD_EMAIL),
    ("Priya Patel", "priya.patel@example.com"),
    ("Marcus Chen", "marcus.chen@example.com"),
    ("Sofia Rossi", "sofia.rossi@example.com"),
]

_DOCUMENT_TYPES = [
    requirement_type
    for requirement_type, kind in INITIAL_REQUIREMENTS
    if kind == RequirementKind.document
]


@dataclass(frozen=True)
class _DemoClub:
    name: str
    description: str
    owner_email: str
    status: ClubStatus
    days_since_update: int
    # Only matters while drafting; every other status needs all four.
    documents: int = len(_DOCUMENT_TYPES)


_PRIYA, _MARCUS, _SOFIA = (email for _, email in DEMO_LEADS[1:])

# fmt: off
_CLUBS = [
    _DemoClub("Chess Club", "Weekly casual and rated games for all levels.", DEMO_LEAD_EMAIL, ClubStatus.drafting, 1, documents=1),
    _DemoClub("Film Society", "Screenings and discussion every Thursday.", DEMO_LEAD_EMAIL, ClubStatus.submitted, 2),
    _DemoClub("Photography Club", "Photo walks, critiques and an end-of-year exhibition.", DEMO_LEAD_EMAIL, ClubStatus.under_review, 1),
    _DemoClub("Debate Society", "Competitive debating and public speaking practice.", DEMO_LEAD_EMAIL, ClubStatus.changes_requested, 4),
    _DemoClub("Robotics Club", "Building robots for the regional competition.", DEMO_LEAD_EMAIL, ClubStatus.approved, 20),
    _DemoClub("Jazz Ensemble", "Rehearsals twice a week and a spring concert.", _PRIYA, ClubStatus.drafting, 3, documents=3),
    _DemoClub("Hiking Club", "Day hikes every other weekend.", _PRIYA, ClubStatus.submitted, 6),
    _DemoClub("Board Games Society", "Board game nights in the student union.", _PRIYA, ClubStatus.rejected, 12),
    _DemoClub("Coding Club", "Hack nights, workshops and a yearly hackathon.", _PRIYA, ClubStatus.approved, 35),
    _DemoClub("Ceramics Club", "Wheel throwing and hand building in the art studio.", _MARCUS, ClubStatus.drafting, 0, documents=0),
    _DemoClub("Astronomy Society", "Telescope nights and talks from visiting researchers.", _MARCUS, ClubStatus.submitted, 9),
    _DemoClub("Climbing Club", "Bouldering sessions and outdoor trips.", _MARCUS, ClubStatus.under_review, 3),
    _DemoClub("Book Club", "One novel a month, discussed over coffee.", _MARCUS, ClubStatus.approved, 60),
    _DemoClub("Dance Club", "Contemporary and hip-hop classes for beginners.", _SOFIA, ClubStatus.submitted, 0),
    _DemoClub("Volunteering Society", "Weekly volunteering with local charities.", _SOFIA, ClubStatus.changes_requested, 7),
    _DemoClub("Model UN", "Simulated UN conferences and diplomacy training.", _SOFIA, ClubStatus.rejected, 25),
]
# fmt: on


def demo_data_exists(db: Session) -> bool:
    emails = [normalize_email(DEMO_ADMIN_EMAIL), normalize_email(DEMO_LEAD_EMAIL)]
    return db.query(User).filter(User.email.in_(emails)).first() is not None


def seed_demo(db: Session) -> None:
    admin = register_user(db, "Demo Admin", DEMO_ADMIN_EMAIL, DEMO_PASSWORD)
    # Updates this same User object, so `admin` is an admin from here on.
    make_admin(db, DEMO_ADMIN_EMAIL)
    leads = {
        email: register_user(db, name, email, DEMO_PASSWORD)
        for name, email in DEMO_LEADS
    }
    for demo in _CLUBS:
        _create_demo_club(db, demo, leads[demo.owner_email], admin)


def _create_demo_club(db: Session, demo: _DemoClub, lead: User, admin: User) -> None:
    club_id = create_club_for_user(db, lead, demo.name, demo.description).id
    for requirement_type in _DOCUMENT_TYPES[: demo.documents]:
        set_requirement_link(
            db, club_id, requirement_type, _demo_link(requirement_type), lead
        )
    _move_to(db, club_id, demo.status, lead, admin)

    # The services stamp everything "now"; spread the clubs over the past weeks
    # so lists, sorting and waiting times look like a real term. History events
    # keep their real time: they are append-only.
    club = db.get_one(Clubs, club_id)
    club.updated_at = datetime.now(UTC) - timedelta(days=demo.days_since_update)
    db.commit()


def _move_to(
    db: Session, club_id: int, status: ClubStatus, lead: User, admin: User
) -> None:
    """Walks a drafting club to `status` the way a lead and an admin would."""
    if status == ClubStatus.drafting:
        return
    submit_club_for_user(db, club_id, lead)
    if status == ClubStatus.submitted:
        return

    review_club(db, club_id, ClubStatus.under_review, admin)
    if status == ClubStatus.under_review:
        # Part-way through the review: two documents checked so far.
        for requirement_type in _DOCUMENT_TYPES[:2]:
            approve_requirement(db, club_id, requirement_type, admin)
    elif status == ClubStatus.changes_requested:
        reject_requirement(
            db, club_id, RequirementType.budget, admin, "The totals don't add up."
        )
        review_club(db, club_id, status, admin, "Please fix the budget and resubmit.")
    elif status == ClubStatus.approved:
        for requirement_type, _ in INITIAL_REQUIREMENTS:
            approve_requirement(db, club_id, requirement_type, admin)
        review_club(db, club_id, status, admin)
    elif status == ClubStatus.rejected:
        review_club(
            db, club_id, status, admin, "Too close to an existing club's purpose."
        )


def _demo_link(requirement_type: RequirementType) -> str:
    return f"https://example.com/demo/{requirement_type.value}"
