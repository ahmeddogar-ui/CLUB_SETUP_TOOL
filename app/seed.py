"""Demo data for trying the app: an admin, a finance approver, four club
leads, sixteen clubs spread over every status, conversations on some of them,
and funding and room booking requests in every status. Built through the services, so every club has the
same requirements and history a real one would. Each service call commits on
its own, so a run that fails partway leaves partial data: reseed into a fresh
database."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Clubs,
    ClubStatus,
    RequestStatus,
    RequirementKind,
    RequirementType,
    User,
    UserRole,
)
from app.request_transitions import RequestAction
from app.request_types import FundingDetails, LineItem, RoomBookingDetails
from app.services.auth import make_admin, normalize_email, register_user
from app.services.clubs import (
    INITIAL_REQUIREMENTS,
    create_club_for_user,
    review_club,
    submit_club_for_user,
)
from app.services.comments import post_comment
from app.services.requests import act_on_request, create_request, list_rooms
from app.services.requirements import (
    approve_requirement,
    reject_requirement,
    set_requirement_link,
)
from app.services.users import change_role

DEMO_ADMIN_EMAIL = "demo-admin@example.com"
DEMO_LEAD_EMAIL = "demo-lead@example.com"
DEMO_FINANCE_EMAIL = "demo-finance@example.com"
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
    finance = register_user(db, "Demo Finance", DEMO_FINANCE_EMAIL, DEMO_PASSWORD)
    change_role(db, admin, finance.id, UserRole.finance_approver)
    club_ids = {
        demo.name: _create_demo_club(db, demo, leads[demo.owner_email], admin)
        for demo in _CLUBS
    }
    _start_conversations(db, club_ids, leads, admin)
    _create_demo_requests(db, club_ids, leads, admin, finance)


def _create_demo_club(db: Session, demo: _DemoClub, lead: User, admin: User) -> int:
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
    return club_id


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


# (club, author: "lead" or "admin", body), in the order they were posted.
_CONVERSATIONS = [
    (
        "Photography Club",
        "lead",
        "Our advisor signs the form on Friday. Is a scan of the signed page enough?",
    ),
    (
        "Photography Club",
        "admin",
        "A scan is fine. The constitution and executive list are already approved.",
    ),
    (
        "Debate Society",
        "admin",
        "The budget totals still don't add up: the travel line is counted twice.",
    ),
    ("Debate Society", "lead", "Thanks, fixing it now and I'll resubmit tonight."),
    ("Climbing Club", "lead", "Do we need a separate waiver for the outdoor trips?"),
]


def _start_conversations(
    db: Session, club_ids: dict[str, int], leads: dict[str, User], admin: User
) -> None:
    owners = {demo.name: leads[demo.owner_email] for demo in _CLUBS}
    for club_name, author, body in _CONVERSATIONS:
        writer = owners[club_name] if author == "lead" else admin
        post_comment(db, club_ids[club_name], writer, body)


# The actions that walk a new draft to each status, as its approvers would.
_WALK_TO: dict[RequestStatus, list[RequestAction]] = {
    RequestStatus.draft: [],
    RequestStatus.submitted: [RequestAction.submit],
    RequestStatus.in_review: [RequestAction.submit, RequestAction.start_review],
    RequestStatus.changes_requested: [
        RequestAction.submit,
        RequestAction.start_review,
        RequestAction.request_changes,
    ],
    RequestStatus.approved: [
        RequestAction.submit,
        RequestAction.start_review,
        RequestAction.approve,
        RequestAction.approve,
    ],
    RequestStatus.rejected: [
        RequestAction.submit,
        RequestAction.start_review,
        RequestAction.reject,
    ],
    RequestStatus.cancelled: [RequestAction.submit, RequestAction.cancel],
}

_NOTES = {
    RequestAction.request_changes: "Please split the venue deposit from the rental.",
    RequestAction.reject: "That week clashes with exams; please pick another.",
}

# fmt: off
# (club, status, title, line items as (description, dollars))
_FUNDING = [
    ("Robotics Club", RequestStatus.draft, "Competition registration", [("Regional entry fee", 350)]),
    ("Robotics Club", RequestStatus.submitted, "Motor and sensor parts", [("Servo motors x6", 210), ("Lidar sensor", 129)]),
    ("Coding Club", RequestStatus.in_review, "Hackathon prizes", [("First prize", 500), ("Runner-up prizes", 300), ("Stickers", 85)]),
    ("Coding Club", RequestStatus.changes_requested, "Winter social", [("Venue rental and deposit", 400), ("Pizza for 60", 360)]),
    ("Book Club", RequestStatus.approved, "Author visit honorarium", [("Honorarium", 250), ("Travel", 120)]),
    ("Book Club", RequestStatus.rejected, "Library trip bus", [("Charter bus", 900)]),
    ("Robotics Club", RequestStatus.cancelled, "Team jackets", [("Jackets x12", 540)]),
]

# (club, status, title, room, days from now, start hour, hours)
_BOOKINGS = [
    ("Robotics Club", RequestStatus.draft, "Build night", "DV 2074", 3, 18, 3),
    ("Coding Club", RequestStatus.submitted, "Intro to Git workshop", "MN 1210", 4, 17, 2),
    ("Book Club", RequestStatus.in_review, "December meeting", "CC 1080", 5, 16, 2),
    ("Robotics Club", RequestStatus.changes_requested, "Demo day rehearsal", "IB 110", 6, 12, 4),
    # Rejected first: its slot is free again for the approved booking below.
    ("Coding Club", RequestStatus.rejected, "Hack night", "DH 2060", 7, 18, 4),
    ("Book Club", RequestStatus.approved, "Author talk", "DH 2060", 7, 18, 3),
    ("Coding Club", RequestStatus.cancelled, "Study session", "DV 2074", 8, 10, 2),
]
# fmt: on


def _create_demo_requests(
    db: Session,
    club_ids: dict[str, int],
    leads: dict[str, User],
    admin: User,
    finance: User,
) -> None:
    owners = {demo.name: leads[demo.owner_email] for demo in _CLUBS}
    for club_name, status, title, items in _FUNDING:
        details = FundingDetails(
            request_type="funding",
            line_items=[
                LineItem(description=description, amount_cents=dollars * 100)
                for description, dollars in items
            ],
        )
        lead = owners[club_name]
        request_id = create_request(
            db, club_ids[club_name], lead, title, details
        ).request.id
        _walk(db, request_id, _WALK_TO[status], lead, [admin, finance])

    rooms = {room.name: room.id for room in list_rooms(db)}
    this_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    for club_name, status, title, room, days, hour, hours in _BOOKINGS:
        starts = this_hour.replace(hour=hour) + timedelta(days=days)
        booking = RoomBookingDetails(
            request_type="room_booking",
            room_id=rooms[room],
            starts_at=starts,
            ends_at=starts + timedelta(hours=hours),
        )
        lead = owners[club_name]
        request_id = create_request(
            db, club_ids[club_name], lead, title, booking
        ).request.id
        # A booking has one approval step, so one approve finishes it.
        actions = _WALK_TO[status]
        if status == RequestStatus.approved:
            actions = actions[:-1]
        _walk(db, request_id, actions, lead, [admin])


def _walk(
    db: Session,
    request_id: int,
    actions: list[RequestAction],
    lead: User,
    approvers: list[User],
) -> None:
    """Takes each action as the right person: the lead submits and cancels;
    approvals go to each step's approver in turn."""
    remaining = iter(approvers)
    approver = next(remaining)
    for action in actions:
        if action in (RequestAction.submit, RequestAction.cancel):
            actor = lead
        else:
            actor = approver
        act_on_request(db, request_id, actor, action, _NOTES.get(action))
        if action == RequestAction.approve:
            approver = next(remaining, approver)
