"""Shared setup for the request tests."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Room
from tests.conftest import auth

# Far enough ahead that "starts in the future" always holds.
TOMORROW_10AM = (datetime.now(UTC) + timedelta(days=1)).replace(
    hour=10, minute=0, second=0, microsecond=0
)


def at(hour: int, minute: int = 0) -> str:
    return TOMORROW_10AM.replace(hour=hour, minute=minute).isoformat()


def a_room(db: Session) -> Room:
    """One of the rooms the migration seeds."""
    room = db.scalars(select(Room).order_by(Room.id)).first()
    assert room is not None
    return room


def funding_body(title="Spring social", items=(("Pizza", 12550), ("Venue", 5000))):
    return {
        "title": title,
        "details": {
            "request_type": "funding",
            "line_items": [
                {"description": description, "amount_cents": cents}
                for description, cents in items
            ],
        },
    }


def booking_body(room_id: int, starts_at: str, ends_at: str, title="Weekly meeting"):
    return {
        "title": title,
        "details": {
            "request_type": "room_booking",
            "room_id": room_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    }


def create_request(client, user, club_id, body):
    response = client.post(
        f"/api/clubs/{club_id}/requests", json=body, headers=auth(user)
    )
    assert response.status_code == 201, response.text
    return response.json()


def act(client, user, request_id, action, note=None):
    body = {"note": note} if note is not None else None
    return client.post(
        f"/api/requests/{request_id}/{action}", json=body, headers=auth(user)
    )


def act_ok(client, user, request_id, action, note=None):
    response = act(client, user, request_id, action, note)
    assert response.status_code == 200, response.text
    return response.json()
