from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    UrlConstraints,
    field_validator,
)

from app.models import (
    ClubStatus,
    EventType,
    RequestStatus,
    RequestType,
    RequirementKind,
    RequirementStatus,
    RequirementType,
    UserRole,
)
from app.request_transitions import RequestAction
from app.request_types import RequestDetails

PERSON_NAME_MAX_LENGTH = 100
# The longest address email-validator accepts (RFC 5321).
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
# Keeps request bodies, and what Argon2 has to hash, bounded.
PASSWORD_MAX_LENGTH = 128
CLUB_NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 2000
NOTE_MAX_LENGTH = 2000
COMMENT_MAX_LENGTH = 2000
REQUEST_TITLE_MAX_LENGTH = 120
URL_MAX_LENGTH = 2048
SEARCH_MAX_LENGTH = 100
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100


# Names and descriptions are trimmed, then required to be non-empty:
# "   " is as missing as "".
PersonName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=PERSON_NAME_MAX_LENGTH
    ),
]
ClubName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=CLUB_NAME_MAX_LENGTH
    ),
]
Description = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=DESCRIPTION_MAX_LENGTH
    ),
]
# Trimmed before the length check, so surrounding spaces never count.
Note = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=NOTE_MAX_LENGTH)
]


class UserRegisterRequest(BaseModel):
    name: PersonName
    email: EmailStr
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    name: PersonName


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


class UserListItemOut(UserOut):
    created_at: datetime


class RoleChangeRequest(BaseModel):
    role: UserRole


class Page[T](BaseModel):
    """One page of a list: `total` counts every match, across all pages."""

    items: list[T]
    total: int


class ClubCreateRequest(BaseModel):
    name: ClubName
    description: Description


class ClubUpdateRequest(BaseModel):
    name: ClubName | None = None
    description: Description | None = None


class ClubOut(BaseModel):
    id: int
    name: str
    description: str
    status: str
    submitter_id: int

    model_config = {"from_attributes": True}


class ClubListItemOut(ClubOut):
    owner_name: str
    updated_at: datetime
    documents_provided: int
    documents_total: int


class ClubPageOut(BaseModel):
    items: list[ClubListItemOut]
    total: int
    status_counts: dict[ClubStatus, int]


class NoteRequest(BaseModel):
    note: Note

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("a note is required for this action")
        return value


class OptionalNoteRequest(BaseModel):
    note: Note | None = None


class RequirementLinkRequest(BaseModel):
    link_url: Annotated[AnyHttpUrl, UrlConstraints(max_length=URL_MAX_LENGTH)]


class ClubEventOut(BaseModel):
    id: int
    event_type: EventType
    requirement_id: int | None
    link_url: str | None
    from_status: ClubStatus | None
    to_status: ClubStatus | None
    note: str | None
    actor_name: str
    created_at: datetime


class RequirementOut(BaseModel):
    id: int
    club_id: int
    requirement_type: RequirementType
    kind: RequirementKind
    status: RequirementStatus
    link_url: str | None
    reviewer_note: str | None

    model_config = {"from_attributes": True}


class CommentRequest(BaseModel):
    body: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=COMMENT_MAX_LENGTH
        ),
    ]


class CommentOut(BaseModel):
    id: int
    body: str
    author_name: str
    author_role: UserRole
    created_at: datetime


class ActivityOut(BaseModel):
    id: int
    event_type: EventType
    created_at: datetime
    actor_id: int
    actor_name: str
    club_id: int | None
    club_name: str | None
    subject_user_id: int | None
    subject_user_name: str | None
    request_id: int | None
    request_title: str | None
    requirement_type: RequirementType | None
    from_status: ClubStatus | None
    to_status: ClubStatus | None
    note: str | None


RequestTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=REQUEST_TITLE_MAX_LENGTH
    ),
]


class RequestCreateRequest(BaseModel):
    title: RequestTitle
    details: RequestDetails


class RequestUpdateRequest(BaseModel):
    title: RequestTitle | None = None
    details: RequestDetails | None = None


class RoomOut(BaseModel):
    id: int
    name: str
    building: str
    capacity: int

    model_config = {"from_attributes": True}


class LineItemOut(BaseModel):
    description: str
    amount_cents: int


class FundingDetailsOut(BaseModel):
    request_type: Literal[RequestType.funding] = RequestType.funding
    line_items: list[LineItemOut]
    total_cents: int


class RoomBookingDetailsOut(BaseModel):
    request_type: Literal[RequestType.room_booking] = RequestType.room_booking
    room_id: int
    room_name: str
    starts_at: datetime
    ends_at: datetime


class ApprovalOut(BaseModel):
    step: int
    role: UserRole
    approver_name: str
    approved_at: datetime
    note: str | None


class RequestListItemOut(BaseModel):
    id: int
    club_id: int
    club_name: str
    request_type: RequestType
    title: str
    status: RequestStatus
    awaiting_role: UserRole | None
    created_by_name: str
    updated_at: datetime
    total_cents: int | None
    room_name: str | None
    starts_at: datetime | None
    ends_at: datetime | None


class RequestDetailOut(BaseModel):
    id: int
    club_id: int
    club_name: str
    request_type: RequestType
    title: str
    status: RequestStatus
    round: int
    awaiting_role: UserRole | None
    created_by_id: int
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    approval_steps: list[UserRole]
    approvals: list[ApprovalOut]
    details: FundingDetailsOut | RoomBookingDetailsOut
    allowed_actions: list[RequestAction]


class RequestEventOut(BaseModel):
    id: int
    event_type: EventType
    actor_name: str
    note: str | None
    created_at: datetime
