from datetime import datetime
from typing import Annotated

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
    RequirementKind,
    RequirementStatus,
    RequirementType,
    UserRole,
)

PERSON_NAME_MAX_LENGTH = 100
# The longest address email-validator accepts (RFC 5321).
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
# Keeps request bodies, and what Argon2 has to hash, bounded.
PASSWORD_MAX_LENGTH = 128
CLUB_NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 2000
NOTE_MAX_LENGTH = 2000
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
    event_type: str
    requirement_id: int | None
    link_url: str | None
    from_status: ClubStatus | None
    to_status: ClubStatus
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
