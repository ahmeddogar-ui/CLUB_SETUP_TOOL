"""Ticket 24: GET /clubs, including the admin review queue (status filter + sort)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Clubs, ClubStatus
from tests.conftest import auth, create_club, make_user

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def set_state(db, club_id, status, days_ago):
    club = db.get(Clubs, club_id)
    club.status = status
    club.updated_at = BASE - timedelta(days=days_ago)
    db.commit()


def list_clubs(client, user, params=None):
    response = client.get("/clubs", params=params, headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()


def ids(clubs):
    return [club["id"] for club in clubs]


@pytest.fixture
def clubs(client, db, lead, other_lead):
    """Five clubs across two owners. Created in id order a..e, but updated_at is
    deliberately NOT in id order, so a correct 'oldest' sort differs from id order."""
    a = create_club(client, lead, name="A")["id"]
    b = create_club(client, lead, name="B")["id"]
    c = create_club(client, other_lead, name="C")["id"]
    d = create_club(client, other_lead, name="D")["id"]
    e = create_club(client, lead, name="E")["id"]
    set_state(db, a, ClubStatus.submitted, days_ago=2)
    set_state(db, b, ClubStatus.drafting, days_ago=9)
    set_state(db, c, ClubStatus.submitted, days_ago=7)
    set_state(db, d, ClubStatus.under_review, days_ago=4)
    set_state(db, e, ClubStatus.submitted, days_ago=5)
    return {"a": a, "b": b, "c": c, "d": d, "e": e}


# --- no parameters: plain listing -------------------------------------------


def test_admin_sees_every_club_in_creation_order(client, admin, clubs):
    assert ids(list_clubs(client, admin)) == [clubs[k] for k in "abcde"]


def test_club_lead_sees_only_own_clubs(client, lead, other_lead, clubs):
    assert ids(list_clubs(client, lead)) == [clubs["a"], clubs["b"], clubs["e"]]
    assert ids(list_clubs(client, other_lead)) == [clubs["c"], clubs["d"]]


def test_club_lead_with_no_clubs_gets_empty_list(client, db, clubs):
    assert list_clubs(client, make_user(db)) == []


def test_response_uses_club_out_shape(client, lead, clubs):
    [first, *_] = list_clubs(client, lead)
    assert set(first) == {"id", "name", "description", "status", "submitter_id"}


def test_requires_auth(client):
    assert client.get("/clubs").status_code == 401


# --- the review queue -------------------------------------------------------


def test_admin_queue_submitted_oldest_first(client, admin, clubs):
    result = list_clubs(client, admin, {"status": "submitted", "sort": "oldest"})
    # c (7 days) -> e (5 days) -> a (2 days); id order would have been a, c, e.
    assert ids(result) == [clubs["c"], clubs["e"], clubs["a"]]
    assert {club["status"] for club in result} == {"submitted"}


def test_admin_queue_submitted_and_under_review(client, admin, clubs):
    result = list_clubs(
        client, admin, [("status", "submitted"), ("status", "under_review"), ("sort", "oldest")]
    )
    assert ids(result) == [clubs["c"], clubs["e"], clubs["d"], clubs["a"]]


def test_status_filter_without_sort_keeps_default_order(client, admin, clubs):
    result = list_clubs(client, admin, {"status": "submitted"})
    assert ids(result) == [clubs["a"], clubs["c"], clubs["e"]]


def test_sort_without_status_filter(client, admin, clubs):
    result = list_clubs(client, admin, {"sort": "oldest"})
    # b (9 days) -> c (7) -> e (5) -> d (4) -> a (2)
    assert ids(result) == [clubs[k] for k in "bceda"]


def test_sort_newest_is_reverse_of_oldest(client, admin, clubs):
    result = list_clubs(client, admin, {"sort": "newest"})
    # a (2 days) -> d (4) -> e (5) -> c (7) -> b (9)
    assert ids(result) == [clubs[k] for k in "adecb"]


def test_admin_recently_decided_view(client, db, admin, clubs):
    set_state(db, clubs["b"], ClubStatus.approved, days_ago=3)
    set_state(db, clubs["d"], ClubStatus.rejected, days_ago=1)
    result = list_clubs(
        client, admin, [("status", "approved"), ("status", "rejected"), ("sort", "newest")]
    )
    assert ids(result) == [clubs["d"], clubs["b"]]


def test_club_lead_newest_still_scoped_to_own_clubs(client, lead, clubs):
    assert ids(list_clubs(client, lead, {"sort": "newest"})) == [
        clubs["a"],
        clubs["e"],
        clubs["b"],
    ]


def test_filter_works_for_any_status(client, admin, clubs):
    assert ids(list_clubs(client, admin, {"status": "drafting"})) == [clubs["b"]]
    assert list_clubs(client, admin, {"status": "approved"}) == []


def test_club_lead_filter_still_scoped_to_own_clubs(client, lead, other_lead, clubs):
    # c is the oldest submitted club overall, but it belongs to other_lead.
    params = {"status": "submitted", "sort": "oldest"}
    assert ids(list_clubs(client, lead, params)) == [clubs["e"], clubs["a"]]
    assert ids(list_clubs(client, other_lead, params)) == [clubs["c"]]


@pytest.mark.parametrize(
    "params",
    [
        {"status": "pending_forever"},
        {"status": "SUBMITTED"},
        {"status": ""},
        {"sort": "sideways"},
        {"sort": "NEWEST"},
    ],
)
def test_invalid_values_rejected_with_422(client, admin, clubs, params):
    response = client.get("/clubs", params=params, headers=auth(admin))
    assert response.status_code == 422
