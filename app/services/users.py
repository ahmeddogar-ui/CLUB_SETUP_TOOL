from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.exceptions import Conflict, NotFound
from app.listing import Page, contains, paginate
from app.models import Clubs, Event, EventType, User, UserRole

# How a role reads in the history ("Club lead → Admin").
ROLE_LABELS = {
    UserRole.admin: "Admin",
    UserRole.club_lead: "Club lead",
}


def list_users(
    db: Session, search: str | None, role: UserRole | None, limit: int, offset: int
) -> Page[User]:
    """By name, then id, so paging is stable; search matches name or email."""
    query = db.query(User)
    if search:
        query = query.filter(
            or_(contains(User.name, search), contains(User.email, search))
        )
    if role:
        query = query.filter(User.role == role)
    return paginate(query.order_by(func.lower(User.name), User.id), limit, offset)


def change_role(db: Session, admin: User, user_id: int, role: UserRole) -> User:
    """Locks the user, so two admins changing one user's role queue up."""
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if user is None:
        raise NotFound("User not found")
    # Keeps at least one admin: the last admin can't demote themselves.
    if user.id == admin.id:
        raise Conflict("You cannot change your own role")
    if user.role == role:
        return user
    owns_clubs = db.query(Clubs.id).filter(Clubs.submitter_id == user.id).first()
    if user.role == UserRole.club_lead and owns_clubs:
        raise Conflict(
            f"{user.name} owns clubs, which only a club lead can submit, "
            "so they stay a club lead"
        )

    db.add(
        Event(
            actor_id=admin.id,
            subject_user_id=user.id,
            event_type=EventType.role_changed,
            note=f"{ROLE_LABELS[user.role]} → {ROLE_LABELS[role]}",
        )
    )
    user.role = role
    db.commit()
    db.refresh(user)
    return user
