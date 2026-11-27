from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint, Range
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


class UserRole(str, Enum):
    admin = "admin"
    club_lead = "club_lead"
    finance_approver = "finance_approver"


class ClubStatus(str, Enum):
    drafting = "drafting"
    submitted = "submitted"
    under_review = "under_review"
    changes_requested = "changes_requested"
    approved = "approved"
    rejected = "rejected"


class RequirementKind(str, Enum):
    document = "document"
    checklist = "checklist"


class RequirementType(str, Enum):
    constitution = "constitution"
    exec_list = "exec_list"
    budget = "budget"
    advisor_form = "advisor_form"
    bank_account_setup = "bank_account_setup"
    exec_onboarding = "exec_onboarding"


class RequirementStatus(str, Enum):
    pending = "pending"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class EventType(str, Enum):
    """Every kind of history entry. Stored as a plain string column, so a new
    kind costs no migration; this enum keeps the code and the activity log's
    filter to the same vocabulary."""

    # A club's registration.
    created = "created"
    submitted = "submitted"
    review_started = "review_started"
    changes_requested = "changes_requested"
    resubmitted = "resubmitted"
    approved = "approved"
    rejected = "rejected"
    # One requirement of a club; the club's status stays put (from == to).
    requirement_submitted = "requirement_submitted"
    requirement_approved = "requirement_approved"
    requirement_rejected = "requirement_rejected"
    # A message in a club's discussion; the body is the note.
    comment_posted = "comment_posted"
    # A user's role; the user is subject_user_id, the change is the note.
    role_changed = "role_changed"
    # A club's request (request_id); one per request action.
    request_created = "request_created"
    request_submitted = "request_submitted"
    request_review_started = "request_review_started"
    request_step_approved = "request_step_approved"
    request_approved = "request_approved"
    request_rejected = "request_rejected"
    request_changes_requested = "request_changes_requested"
    request_cancelled = "request_cancelled"


class RequestType(str, Enum):
    funding = "funding"
    room_booking = "room_booking"


class RequestStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    in_review = "in_review"
    changes_requested = "changes_requested"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


# Waiting on an approver: awaiting_role is set exactly while in these.
AWAITING_APPROVAL_STATUSES = (RequestStatus.submitted, RequestStatus.in_review)
# A booking in these holds its room; draft, rejected and cancelled don't.
SLOT_HOLDING_STATUSES = (
    RequestStatus.submitted,
    RequestStatus.in_review,
    RequestStatus.changes_requested,
    RequestStatus.approved,
)


def _status_list(statuses: tuple[RequestStatus, ...]) -> str:
    return ", ".join(f"'{status.value}'" for status in statuses)


# A document counts as provided once a link is in and hasn't been rejected.
DOCUMENT_PROVIDED_STATUSES = (RequirementStatus.submitted, RequirementStatus.approved)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Clubs(Base):
    __tablename__ = "clubs"
    __table_args__ = (
        # The review queue and status tabs: filter by status, sort by updated_at.
        Index("idx_clubs_status_updated", "status", "updated_at"),
        # A lead's own clubs, newest first.
        Index("idx_clubs_submitter_updated", "submitter_id", "updated_at", "id"),
        # The admin's All tab, newest first (scanned backwards).
        Index("idx_clubs_updated", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    status: Mapped[ClubStatus] = mapped_column(SAEnum(ClubStatus))
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("club_id", "requirement_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"))
    requirement_type: Mapped[RequirementType] = mapped_column(
        SAEnum(RequirementType, name="requirement_type")
    )
    kind: Mapped[RequirementKind] = mapped_column(
        SAEnum(RequirementKind, name="requirement_kind")
    )
    link_url: Mapped[str | None]
    status: Mapped[RequirementStatus] = mapped_column(
        SAEnum(RequirementStatus, name="requirement_status"),
        server_default=RequirementStatus.pending.value,
    )
    reviewer_note: Mapped[str | None]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )


class Event(Base):
    """The app's one append-only history: every club, requirement, comment and
    role action is a row here. A club's history and the admin's activity log
    are both views of it."""

    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "club_id IS NOT NULL OR subject_user_id IS NOT NULL",
            name="about_club_or_user",
        ),
        # A club's history (and its comments): filter by club, newest first.
        Index("idx_events_club_time", "club_id", text("created_at DESC")),
        # The activity log: everything, by actor, or by type, newest first.
        Index("idx_events_time", text("created_at DESC"), text("id DESC")),
        Index("idx_events_actor_time", "actor_id", text("created_at DESC")),
        Index("idx_events_type_time", "event_type", text("created_at DESC")),
        # A request's history.
        Index("idx_events_request_time", "request_id", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT, not CASCADE: history is append-only (a trigger rejects deletes),
    # so a club with history can't be deleted either.
    club_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id", ondelete="RESTRICT")
    )
    # The request an event is about (request_* events, which also name its club).
    request_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"))
    # The user an event is about when it isn't about a club (role_changed).
    subject_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # An EventType value. Requirement events name WHICH requirement through
    # requirement_id, never in the string ("requirement_rejected", not
    # "budget_rejected"), so "all rejections" stays an equality.
    event_type: Mapped[str]
    requirement_id: Mapped[int | None] = mapped_column(ForeignKey("requirements.id"))
    # For requirement_submitted: the exact link provided, so the history shows which
    # version of a document each later approve/reject decision was about.
    link_url: Mapped[str | None]
    # The club's status around a club event; empty for comments and role changes.
    from_status: Mapped[ClubStatus | None] = mapped_column(SAEnum(ClubStatus))
    to_status: Mapped[ClubStatus | None] = mapped_column(SAEnum(ClubStatus))
    # A reviewer's reason, a comment's body, or a role change ("Club lead → Admin").
    # Stored per event so each review round keeps its own note.
    note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Room(Base):
    """A bookable room. Reference data, seeded by the migration that adds it."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    building: Mapped[str]
    capacity: Mapped[int]


class Request(Base):
    """Something an approved club asks for. Every type shares this row, its
    state machine and its approval chain (app/request_types.py); a type's own
    data lives in its columns (room booking) or child rows (funding)."""

    __tablename__ = "requests"
    __table_args__ = (
        # Booking columns are filled exactly for room bookings.
        CheckConstraint(
            "(request_type = 'room_booking') = "
            "(room_id IS NOT NULL AND booked_during IS NOT NULL)",
            name="booking_fields_match_type",
        ),
        # Set exactly while the request waits for an approver.
        CheckConstraint(
            f"(awaiting_role IS NOT NULL) = "
            f"(status IN ({_status_list(AWAITING_APPROVAL_STATUSES)}))",
            name="awaiting_role_matches_status",
        ),
        CheckConstraint(
            "NOT isempty(booked_during) AND NOT lower_inf(booked_during) "
            "AND NOT upper_inf(booked_during)",
            name="booking_bounded",
        ),
        # No double booking: two bookings that hold a slot can't overlap in
        # one room. Ranges are [start, end), so back-to-back bookings fit.
        ExcludeConstraint(
            ("room_id", "="),
            ("booked_during", "&&"),
            name="no_double_booking",
            using="gist",
            where=text(f"status IN ({_status_list(SLOT_HOLDING_STATUSES)})"),
        ),
        # A club's Requests tab, newest first; id breaks ties, as the query does.
        Index("idx_requests_club_updated", "club_id", "updated_at", "id"),
        # The review queue: what waits for a role, oldest first.
        Index("idx_requests_awaiting_updated", "awaiting_role", "updated_at", "id"),
        # An approver's unfiltered list, newest first.
        Index("idx_requests_updated", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"))
    request_type: Mapped[RequestType] = mapped_column(
        SAEnum(RequestType, name="request_type_kind")
    )
    title: Mapped[str]
    status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus))
    # Each submit starts a new round of approvals; 0 until the first submit.
    round: Mapped[int] = mapped_column(server_default=text("0"))
    # The role whose approval the request waits for; derived from the type's
    # steps and this round's approvals, stored so the queue is one indexed query.
    awaiting_role: Mapped[UserRole | None] = mapped_column(SAEnum(UserRole))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    booked_during: Mapped[Range[datetime] | None] = mapped_column(TSTZRANGE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )


class FundingLineItem(Base):
    __tablename__ = "funding_line_items"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        UniqueConstraint("request_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE")
    )
    position: Mapped[int]
    description: Mapped[str]
    # Whole cents: exact arithmetic, no floating point.
    amount_cents: Mapped[int]


class RequestApproval(Base):
    """One approver's sign-off on one step of one round. The unique constraint
    makes a second approval of the same step impossible."""

    __tablename__ = "request_approvals"
    __table_args__ = (UniqueConstraint("request_id", "round", "step"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE")
    )
    round: Mapped[int]
    step: Mapped[int]
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None]
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class RefreshToken(Base):
    """Long-lived login, kept in an httpOnly cookie and exchanged at
    /api/auth/refresh for short-lived access tokens. Only a hash is stored, so a
    database leak doesn't hand out working tokens."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
