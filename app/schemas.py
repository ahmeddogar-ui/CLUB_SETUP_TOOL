from datetime import datetime
from typing import Annotated

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.models import (
    ClubStatus,
    RequirementKind,
    RequirementStatus,
    RequirementType,
    UserRole,
)

# Trimmed, then required to be non-empty: "   " is as missing as "".
NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class UserRegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class ClubCreateRequest(BaseModel):
    name: NonBlankStr
    description: NonBlankStr


class ClubUpdateRequest(BaseModel):
    name: NonBlankStr | None = None
    description: NonBlankStr | None = None


class ClubOut(BaseModel):
    id: int
    name: str
    description: str
    status: str
    submitter_id: int

    model_config = {"from_attributes": True}


class NoteRequest(BaseModel):
    note: str

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a note is required for this action")
        return value.strip()


class OptionalNoteRequest(BaseModel):
    note: str | None = None


class RequirementLinkRequest(BaseModel):
    link_url: AnyHttpUrl


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
