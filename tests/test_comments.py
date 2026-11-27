"""A club's discussion thread: GET/POST /clubs/{id}/comments."""

import pytest

from app.models import ClubStatus
from tests.conftest import auth, make_club


@pytest.fixture
def club(db, lead):
    return make_club(db, lead, status=ClubStatus.under_review)


def post(client, user, club_id, body):
    return client.post(
        f"/api/clubs/{club_id}/comments", json={"body": body}, headers=auth(user)
    )


def comments(client, user, club_id, **params):
    return client.get(
        f"/api/clubs/{club_id}/comments", params=params, headers=auth(user)
    )


def test_owner_and_admin_discuss_a_club(client, club, lead, admin):
    assert post(client, lead, club.id, "  Is the budget OK now?  ").status_code == 201
    reply = post(client, admin, club.id, "Yes, thanks.")
    assert reply.status_code == 201
    assert set(reply.json()) == {
        "id",
        "body",
        "author_name",
        "author_role",
        "created_at",
    }

    page = comments(client, lead, club.id).json()

    assert page["total"] == 2
    # Newest first.
    assert [item["body"] for item in page["items"]] == [
        "Yes, thanks.",
        "Is the budget OK now?",
    ]
    assert page["items"][0]["author_name"] == admin.name
    assert page["items"][0]["author_role"] == "admin"


def test_comments_page(client, club, lead):
    for number in range(3):
        post(client, lead, club.id, f"comment {number}")

    page = comments(client, lead, club.id, limit=2, offset=2).json()

    assert page["total"] == 3
    assert [item["body"] for item in page["items"]] == ["comment 0"]


def test_strangers_can_neither_read_nor_post(client, club, other_lead):
    assert comments(client, other_lead, club.id).status_code == 403
    assert post(client, other_lead, club.id, "hi").status_code == 403


def test_missing_club_is_404(client, lead):
    assert comments(client, lead, 999_999).status_code == 404
    assert post(client, lead, 999_999, "hi").status_code == 404


@pytest.mark.parametrize("body", ["", "   ", "x" * 2001])
def test_blank_or_overlong_comment_is_422(client, club, lead, body):
    assert post(client, lead, club.id, body).status_code == 422


def test_comments_stay_out_of_the_club_history(client, club, lead):
    post(client, lead, club.id, "hello")

    history = client.get(f"/api/clubs/{club.id}/events", headers=auth(lead)).json()

    assert [event["event_type"] for event in history] == ["created"]
