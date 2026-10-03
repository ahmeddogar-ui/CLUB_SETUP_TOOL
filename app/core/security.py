from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import User, UserRole
from pwdlib import PasswordHash
import jwt
import secrets
from datetime import datetime, timedelta, timezone

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

SESSION_USER_KEY = "user_id"
SESSION_CSRF_KEY = "csrf_token"


def get_current_user_from_session(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """Browser-facing counterpart to get_current_user. The API authenticates
    each call with a JWT in the Authorization header; pages instead keep the
    logged-in user's id in Starlette's signed session cookie (see
    SessionMiddleware in main.py), which the browser sends back on every
    navigation and form POST automatically.

    Returns None rather than raising on any failure (no session, unknown
    user) -- callers decide what "not logged in" should do (e.g. render a
    logged-out page vs. redirect to /login), instead of this dependency
    always forcing a 401 the way the API's get_current_user correctly does
    for a real API client.
    """
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_csrf_token(request: Request) -> str:
    """The per-session token embedded as a hidden field in every form."""
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


async def verify_csrf(request: Request) -> None:
    """Dependency for browser POST routes: the form's hidden csrf_token must
    match the one stored in the session. A forged cross-site form can't read
    the token, so it can't supply it.
    """
    form = await request.form()
    submitted = form.get("csrf_token")
    expected = request.session.get(SESSION_CSRF_KEY)
    if (
        not expected
        or not isinstance(submitted, str)
        or not secrets.compare_digest(submitted, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )


def require_web_user(
    user: User | None = Depends(get_current_user_from_session),
) -> User:
    """Use on any browser page that requires being logged in. Redirects to
    /login instead of returning a bare 401 -- a person clicking a link
    should land on a form, not a JSON error body.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def require_web_role(required_role: UserRole):
    def role_checker(user: User = Depends(require_web_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this page",
            )
        return user

    return role_checker


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user
    return role_checker