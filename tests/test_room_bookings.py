"""No double booking: a Postgres exclusion constraint on overlapping ranges for
one room, over pending and approved bookings only."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range

from app.models import ClubStatus, Request, Room
from tests.conftest import auth, make_club
from tests.request_helpers import a_room, act, act_ok, at, booking_body, create_request


@pytest.fixture
def club(db, lead):
    return make_club(db, lead, status=ClubStatus.approved)


@pytest.fixture
def room(db):
    return a_room(db)


def book(client, lead, club, room, starts, ends):
    request = create_request(client, lead, club.id, booking_body(room.id, starts, ends))
    return request["id"], act(client, lead, request["id"], "submit")


def test_rooms_are_listed(client, db, lead):
    rooms = client.get("/api/rooms", headers=auth(lead)).json()
    assert len(rooms) >= 4
    assert set(rooms[0]) == {"id", "name", "building", "capacity"}


def test_an_overlapping_booking_is_refused_with_a_clear_message(
    client, lead, club, room
):
    _, first = book(client, lead, club, room, at(10), at(12))
    assert first.status_code == 200
    second_id, second = book(client, lead, club, room, at(11), at(13))

    assert second.status_code == 409
    assert second.json()["detail"] == (
        f"{room.name} is already booked for part of that time. "
        "Choose another time or room."
    )
    detail = client.get(f"/api/requests/{second_id}", headers=auth(lead)).json()
    assert detail["status"] == "draft"


def test_back_to_back_bookings_both_fit(client, lead, club, room):
    assert book(client, lead, club, room, at(10), at(11))[1].status_code == 200
    assert book(client, lead, club, room, at(11), at(12))[1].status_code == 200


def test_another_room_at_the_same_time_is_fine(client, db, lead, club, room):
    other = db.scalars(select(Room).where(Room.id != room.id)).first()
    assert book(client, lead, club, room, at(10), at(11))[1].status_code == 200
    assert book(client, lead, club, other, at(10), at(11))[1].status_code == 200


def test_a_draft_holds_no_slot(client, lead, club, room):
    create_request(client, lead, club.id, booking_body(room.id, at(10), at(11)))
    assert book(client, lead, club, room, at(10), at(11))[1].status_code == 200


@pytest.mark.parametrize("ending", ["reject", "cancel"])
def test_a_rejected_or_cancelled_booking_frees_the_slot(
    client, lead, admin, club, room, ending
):
    first_id, _ = book(client, lead, club, room, at(10), at(11))
    if ending == "reject":
        act_ok(client, admin, first_id, "start-review")
        act_ok(client, admin, first_id, "reject", note="Room closed")
    else:
        act_ok(client, lead, first_id, "cancel")

    assert book(client, lead, club, room, at(10), at(11))[1].status_code == 200


def test_an_approved_booking_keeps_its_slot(client, lead, admin, club, room):
    first_id, _ = book(client, lead, club, room, at(10), at(11))
    act_ok(client, admin, first_id, "start-review")
    act_ok(client, admin, first_id, "approve")
    assert book(client, lead, club, room, at(10), at(11))[1].status_code == 409


def test_moving_a_booking_into_a_taken_slot_during_changes_is_409(
    client, lead, admin, club, room
):
    book(client, lead, club, room, at(14), at(15))
    moving_id, _ = book(client, lead, club, room, at(10), at(11))
    act_ok(client, admin, moving_id, "start-review")
    act_ok(client, admin, moving_id, "request-changes", note="Later please")

    response = client.patch(
        f"/api/requests/{moving_id}",
        json={"details": booking_body(room.id, at(14, 30), at(15, 30))["details"]},
        headers=auth(lead),
    )

    assert response.status_code == 409
    assert "already booked" in response.json()["detail"]


@pytest.mark.parametrize(
    "starts, ends",
    [
        (at(11), at(10)),  # ends before it starts
        (at(10), at(10)),  # empty
        (at(8), at(21)),  # longer than 12 hours
    ],
)
def test_impossible_time_ranges_are_422(client, lead, club, room, starts, ends):
    response = client.post(
        f"/api/clubs/{club.id}/requests",
        json=booking_body(room.id, starts, ends),
        headers=auth(lead),
    )
    assert response.status_code == 422


def test_a_booking_in_the_past_is_422(client, lead, club, room):
    yesterday = datetime.now(UTC) - timedelta(days=1)
    response = client.post(
        f"/api/clubs/{club.id}/requests",
        json=booking_body(
            room.id, yesterday.isoformat(), (yesterday + timedelta(hours=1)).isoformat()
        ),
        headers=auth(lead),
    )
    assert response.status_code == 422


def test_an_unknown_room_is_404(client, lead, club):
    response = client.post(
        f"/api/clubs/{club.id}/requests",
        json=booking_body(999_999, at(10), at(11)),
        headers=auth(lead),
    )
    assert response.status_code == 404


def _start_in_the_past(db, request_id):
    """A draft made for a time that has since passed (the details check only
    runs when they are entered)."""
    request = db.get(Request, request_id)
    starts = datetime.now(UTC) - timedelta(hours=2)
    request.booked_during = Range(starts, starts + timedelta(hours=1), bounds="[)")
    db.commit()


def test_a_booking_whose_time_has_passed_cant_be_submitted(
    client, db, lead, club, room
):
    draft = create_request(client, lead, club.id, booking_body(room.id, at(10), at(11)))
    _start_in_the_past(db, draft["id"])

    response = act(client, lead, draft["id"], "submit")

    assert response.status_code == 409
    assert "already started" in response.json()["detail"]


def test_a_booking_whose_time_has_passed_cant_be_approved(
    client, db, lead, admin, club, room
):
    request_id, _ = book(client, lead, club, room, at(10), at(11))
    act_ok(client, admin, request_id, "start-review")
    _start_in_the_past(db, request_id)

    assert act(client, admin, request_id, "approve").status_code == 409
    detail = client.get(f"/api/requests/{request_id}", headers=auth(admin)).json()
    assert detail["allowed_actions"] == ["reject", "request_changes"]


def test_an_approved_booking_that_has_started_cant_be_cancelled(
    client, db, lead, admin, club, room
):
    request_id, _ = book(client, lead, club, room, at(10), at(11))
    act_ok(client, admin, request_id, "start-review")
    act_ok(client, admin, request_id, "approve")
    _start_in_the_past(db, request_id)

    assert act(client, lead, request_id, "cancel").status_code == 409
