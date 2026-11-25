from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Response, status

from app.core.config import settings
from app.core.security import get_current_user
from app.database import DbSession
from app.models import User
from app.schemas import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    UserOut,
    UserRegisterRequest,
)
from app.services.auth import (
    log_in,
    refresh_access_token,
    register_user,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


# Path "/" so the browser sends the cookie both to /auth/* directly and to
# /api/auth/* through the frontend's proxy. httpOnly keeps it away from page
# scripts; SameSite=strict keeps it off cross-site requests.
def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
        httponly=True,
        secure=settings.SESSION_HTTPS_ONLY,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path="/",
        httponly=True,
        secure=settings.SESSION_HTTPS_ONLY,
        samesite="strict",
    )


def _bearer(access_token: str) -> dict[str, str]:
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: DbSession):
    return register_user(db, payload.name, payload.email, payload.password)


# Form fields, as the OAuth2 password flow sends them; named and bounded here
# rather than taken from OAuth2PasswordRequestForm, which has no length limits.
@router.post("/login")
def login(
    response: Response,
    db: DbSession,
    username: Annotated[str, Form(max_length=EMAIL_MAX_LENGTH)],
    password: Annotated[str, Form(max_length=PASSWORD_MAX_LENGTH)],
):
    access_token, refresh_token = log_in(db, username, password)
    _set_refresh_cookie(response, refresh_token)
    return _bearer(access_token)


@router.post("/refresh")
def refresh(db: DbSession, refresh_token: RefreshCookie = None):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in"
        )
    return _bearer(refresh_access_token(db, refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbSession, refresh_token: RefreshCookie = None):
    if refresh_token is not None:
        revoke_refresh_token(db, refresh_token)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
