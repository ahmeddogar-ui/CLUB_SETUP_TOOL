from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user
from app.database import DbSession
from app.models import User
from app.schemas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    CommentOut,
    CommentRequest,
    Page,
)
from app.services.comments import list_comments, post_comment

router = APIRouter(prefix="/clubs", tags=["comments"])


@router.get("/{club_id}/comments", response_model=Page[CommentOut])
def get_comments(
    club_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    offset: int = Query(default=0, ge=0),
):
    page = list_comments(db, club_id, current_user, limit, offset)
    return Page(
        items=[CommentOut(**asdict(comment)) for comment in page.items],
        total=page.total,
    )


@router.post(
    "/{club_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    club_id: int,
    payload: CommentRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return CommentOut(**asdict(post_comment(db, club_id, current_user, payload.body)))
