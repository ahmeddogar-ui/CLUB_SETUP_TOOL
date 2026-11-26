from datetime import UTC, datetime, timedelta

from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.exceptions import Conflict, Forbidden, Unauthorized
from app.models import RefreshToken, User, UserRole

UNIQUE_EMAIL_CONSTRAINT = "uq_users_email"


def normalize_email(email: str) -> str:
    """Emails are stored and compared lowercased (the DB enforces it), so
    Ada@example.com and ada@example.com are one account."""
    return email.strip().lower()


def register_user(db: Session, name: str, email: str, password: str) -> User:
    user = User(
        name=name,
        email=normalize_email(email),
        password_hash=hash_password(password),
        role=UserRole.club_lead,
    )
    db.add(user)
    # Let the unique constraint decide: a check-then-insert would race when two
    # registrations for one email arrive together.
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        is_duplicate_email = (
            isinstance(error.orig, UniqueViolation)
            and error.orig.diag.constraint_name == UNIQUE_EMAIL_CONSTRAINT
        )
        if is_duplicate_email:
            raise Conflict("User already exists") from error
        raise
    db.refresh(user)
    return user


def _verify_credentials(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == normalize_email(email)).first()
    if not user or not verify_password(password, user.password_hash):
        raise Unauthorized("Incorrect email or password")
    return user


def log_in(db: Session, email: str, password: str) -> tuple[str, str]:
    """Returns (access token, refresh token), or raises Unauthorized."""
    user = _verify_credentials(db, email, password)
    refresh_token = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return create_access_token(user.id), refresh_token


def _find_refresh_token(db: Session, refresh_token: str) -> RefreshToken | None:
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(refresh_token))
        .first()
    )


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """Returns a new access token for a known, unexpired, unrevoked refresh
    token, or raises Unauthorized."""
    stored = _find_refresh_token(db, refresh_token)
    if (
        stored is None
        or stored.revoked_at is not None
        or stored.expires_at <= datetime.now(UTC)
    ):
        raise Unauthorized("Invalid refresh token")
    return create_access_token(stored.user_id)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    """Idempotent: an unknown or already-revoked token is left as it is."""
    stored = _find_refresh_token(db, refresh_token)
    if stored is None or stored.revoked_at is not None:
        return
    stored.revoked_at = datetime.now(UTC)
    db.commit()


def make_admin(db: Session, email: str) -> User | None:
    """Gives an existing user the admin role. None if no such user."""
    user = db.query(User).filter(User.email == normalize_email(email)).first()
    if user is None:
        return None
    user.role = UserRole.admin
    db.commit()
    db.refresh(user)
    return user


def update_name(db: Session, user: User, name: str) -> User:
    user.name = name
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
    keep_refresh_token: str | None,
) -> None:
    """Sets a new password and signs the user out everywhere else: every
    refresh token is revoked except `keep_refresh_token`, the current session's.
    Raises Forbidden (not Unauthorized: the session itself is fine) if the
    current password is wrong."""
    if not verify_password(current_password, user.password_hash):
        raise Forbidden("Current password is incorrect")
    user.password_hash = hash_password(new_password)

    kept_hash = hash_refresh_token(keep_refresh_token) if keep_refresh_token else None
    other_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.token_hash != kept_hash,
    )
    other_tokens.update({RefreshToken.revoked_at: datetime.now(UTC)})
    db.commit()
