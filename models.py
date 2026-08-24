from sqlalchemy import DateTime, ForeignKey, MetaData, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase
from enum import Enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum, MetaData
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

class ClubStatus(str, Enum):
    drafting = "drafting"
    submitted = "submitted"
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

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole)
    )
    email: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Clubs(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[ClubStatus] = mapped_column(
        SAEnum(ClubStatus)
    )
    submitter_id: Mapped[int] = mapped_column(
    ForeignKey("users.id")
)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint("club_id", "requirement_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE")
    )
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

    