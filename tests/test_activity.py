"""The admin's activity log: GET /activity over the one append-only event table."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import ClubStatus, Event
from tests.conftest import auth, make_club


def activity(client, admin, **params):
    response = client.get("/api/activity", params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def history(client, db, admin, lead, other_lead):
    """Two clubs, a comment and a role change."""
    chess = make_club(db, lead, status=ClubStatus.submitted, name="Chess Club")
    film = make_club(db, other_lead, name="Film Club")
    client.post(
        f"/api/clubs/{chess.id}/comments", json={"body": "Hi"}, headers=auth(admin)
    )
    client.post(f"/api/clubs/{chess.id}/start-review", headers=auth(admin))
    return {"chess": chess, "film": film}


def test_newest_first_with_names(client, admin, lead, history):
    page = activity(client, admin, club_id=history["chess"].id)

    assert [item["event_type"] for item in page["items"]] == [
        "review_started",
        "comment_posted",
        "created",
    ]
    assert page["total"] == 3
    newest = page["items"][0]
    assert newest["actor_name"] == admin.name
    assert newest["club_name"] == "Chess Club"
    assert newest["from_status"] == "submitted"
    assert newest["to_status"] == "under_review"
    assert page["items"][1]["note"] == "Hi"


def test_filters_by_actor_and_type(client, admin, other_lead, history):
    by_actor = activity(client, admin, actor_id=other_lead.id)
    by_type = activity(
        client, admin, event_type="comment_posted", club_id=history["chess"].id
    )

    assert [item["club_name"] for item in by_actor["items"]] == ["Film Club"]
    assert [item["note"] for item in by_type["items"]] == ["Hi"]


def test_filters_by_date_range(client, db, admin, history):
    club_id = history["chess"].id
    now = datetime.now(UTC)
    later = (now + timedelta(days=1)).isoformat()
    earlier = (now - timedelta(days=1)).isoformat()

    assert activity(client, admin, club_id=club_id, since=later)["total"] == 0
    assert activity(client, admin, club_id=club_id, until=earlier)["total"] == 0
    assert (
        activity(client, admin, club_id=club_id, since=earlier, until=later)["total"]
        == 3
    )


def test_role_changes_name_the_user_not_a_club(client, admin, lead):
    lead_without_clubs = lead
    client.patch(
        f"/api/users/{lead_without_clubs.id}/role",
        json={"role": "admin"},
        headers=auth(admin),
    )

    [item] = activity(client, admin, event_type="role_changed", actor_id=admin.id)[
        "items"
    ]

    assert item["club_id"] is None
    assert item["club_name"] is None
    assert item["subject_user_name"] == lead.name
    assert item["note"] == "Club lead → Admin"


def test_pages(client, admin, history):
    page = activity(client, admin, club_id=history["chess"].id, limit=1, offset=1)
    assert page["total"] == 3
    assert [item["event_type"] for item in page["items"]] == ["comment_posted"]


def test_unknown_event_type_is_422_and_non_admin_403(client, admin, lead):
    bad = client.get(
        "/api/activity", params={"event_type": "nope"}, headers=auth(admin)
    )
    assert bad.status_code == 422
    assert client.get("/api/activity", headers=auth(lead)).status_code == 403


def test_an_event_must_be_about_a_club_or_a_user(db, admin):
    db.add(Event(actor_id=admin.id, event_type="role_changed"))
    with pytest.raises(IntegrityError, match="about_club_or_user"):
        db.flush()


def test_events_stay_append_only_after_the_rename(db, admin, lead):
    club = make_club(db, lead)
    with pytest.raises(Exception, match="append-only"):
        db.execute(text("DELETE FROM events WHERE club_id = :id"), {"id": club.id})


def test_request_events_name_their_request(client, db, admin, lead):
    from tests.request_helpers import create_request, funding_body

    club = make_club(db, lead, status=ClubStatus.approved)
    request = create_request(client, lead, club.id, funding_body(title="Spring social"))

    [item] = activity(client, admin, event_type="request_created", club_id=club.id)[
        "items"
    ]

    assert item["request_id"] == request["id"]
    assert item["request_title"] == "Spring social"
    assert item["club_name"] == club.name
