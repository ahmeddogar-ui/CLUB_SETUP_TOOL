from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.exceptions import Conflict, Forbidden, NotFound
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


def ensure_role_change_allowed(db: Session, user: User, role: UserRole) -> None:
    """A lead's clubs can only ever be submitted by a club lead, so a lead who
    owns clubs keeps the role. Shared with the make-admin command."""
    owns_clubs = db.query(Clubs.id).filter(Clubs.submitter_id == user.id).first()
    if user.role == UserRole.club_lead and role != user.role and owns_clubs:
        raise Conflict(
            f"{user.name} owns clubs, which only a club lead can submit, "
            "so they stay a club lead"
        )


def change_role(db: Session, admin: User, user_id: int, role: UserRole) -> User:
    """Locks the acting admin and the user, in id order so two admins acting on
    each other can't deadlock, then re-checks the actor: if two admins demote
    each other at once, the second finds they are no longer an admin. With
    "you can't change your own role", that keeps at least one admin."""
    locked = {
        locked_user.id: locked_user
        for locked_user in db.query(User)
        .filter(User.id.in_({admin.id, user_id}))
        .order_by(User.id)
        .with_for_update()
        .populate_existing()
    }
    user = locked.get(user_id)
    if user is None:
        raise NotFound("User not found")
    if locked[admin.id].role != UserRole.admin:
        raise Forbidden("You are no longer an admin")
    if user.id == admin.id:
        raise Conflict("You cannot change your own role")
    if user.role == role:
        return user
    ensure_role_change_allowed(db, user, role)

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
