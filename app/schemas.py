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
PASSWORD_MIN_LENGTH = 8
# Argon2 hashes any length, but an unbounded password lets one request burn CPU.
PASSWORD_MAX_LENGTH = 128
CLUB_NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 2000
NOTE_MAX_LENGTH = 2000
URL_MAX_LENGTH = 2048


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
Note = Annotated[str, StringConstraints(max_length=NOTE_MAX_LENGTH)]


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


class NoteRequest(BaseModel):
    note: Note

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a note is required for this action")
        return value.strip()


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
