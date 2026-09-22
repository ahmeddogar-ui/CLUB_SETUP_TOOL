from pydantic import BaseModel, EmailStr, Field

from app.models import UserRole


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
