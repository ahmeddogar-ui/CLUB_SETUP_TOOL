from fastapi import APIRouter, Depends, Query

from app.core.security import require_role
from app.database import DbSession
from app.models import User, UserRole
from app.schemas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    SEARCH_MAX_LENGTH,
    Page,
    RoleChangeRequest,
    UserListItemOut,
    UserOut,
)
from app.services.users import change_role, list_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserListItemOut])
def get_users(
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
    q: str | None = Query(default=None, max_length=SEARCH_MAX_LENGTH),
    role: UserRole | None = None,
    limit: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    offset: int = Query(default=0, ge=0),
):
    page = list_users(db, search=q, role=role, limit=limit, offset=offset)
    return Page(
        items=[UserListItemOut.model_validate(user) for user in page.items],
        total=page.total,
    )


@router.patch("/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    payload: RoleChangeRequest,
    db: DbSession,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return change_role(db, current_user, user_id, payload.role)
