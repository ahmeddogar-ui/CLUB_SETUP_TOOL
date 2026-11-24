from fastapi import HTTPException, status
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole

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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            ) from error
        raise
    db.refresh(user)
    return user


def verify_credentials(db: Session, email: str, password: str) -> User:
    """Returns the user, or raises 401. Shared by the JWT API and the web session."""
    user = db.query(User).filter(User.email == normalize_email(email)).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def authenticate_user(db: Session, email: str, password: str) -> str:
    """Returns a fresh access token, or raises 401."""
    return create_access_token(verify_credentials(db, email, password).id)


def make_admin(db: Session, email: str) -> User | None:
    """Gives an existing user the admin role. None if no such user."""
    user = db.query(User).filter(User.email == normalize_email(email)).first()
    if user is None:
        return None
    user.role = UserRole.admin
    db.commit()
    db.refresh(user)
    return user
