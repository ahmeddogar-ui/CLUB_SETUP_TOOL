from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator

from app.models import RequirementKind, RequirementStatus, RequirementType, UserRole


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
    name: str
    description: str


class ClubUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


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


class RequirementOut(BaseModel):
    id: int
    club_id: int
    requirement_type: RequirementType
    kind: RequirementKind
    status: RequirementStatus
    link_url: str | None
    reviewer_note: str | None

    model_config = {"from_attributes": True}
