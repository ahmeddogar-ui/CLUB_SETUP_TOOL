from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_role
from app.database import DbSession
from app.models import RequirementType, User, UserRole
from app.schemas import (
    NoteRequest,
    OptionalNoteRequest,
    RequirementLinkRequest,
    RequirementOut,
)
from app.services import requirements as service

router = APIRouter(prefix="/clubs", tags=["requirements"])


@router.put(
    "/{club_id}/requirements/{requirement_type}/link",
    response_model=RequirementOut,
)
def set_requirement_link(
    club_id: int,
    requirement_type: RequirementType,
    payload: RequirementLinkRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return service.set_requirement_link(
        db, club_id, requirement_type, str(payload.link_url), current_user
    )


@router.post(
    "/{club_id}/requirements/{requirement_type}/approve",
    response_model=RequirementOut,
)
def approve_requirement(
    club_id: int,
    requirement_type: RequirementType,
    db: DbSession,
    payload: OptionalNoteRequest | None = None,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return service.approve_requirement(
        db, club_id, requirement_type, current_user, payload.note if payload else None
    )


@router.post(
    "/{club_id}/requirements/{requirement_type}/reject",
    response_model=RequirementOut,
)
def reject_requirement(
    club_id: int,
    requirement_type: RequirementType,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return service.reject_requirement(
        db, club_id, requirement_type, current_user, payload.note
    )
