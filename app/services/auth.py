from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole


def register_user(db: Session, name: str, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.club_lead,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_credentials(db: Session, email: str, password: str) -> User:
    """Returns the user, or raises 401. Shared by the JWT API and the web session."""
    user = db.query(User).filter(User.email == email).first()
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
