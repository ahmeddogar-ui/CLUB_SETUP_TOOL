"""Ticket 23: admin-only routes reject non-admins at the dependency layer.

The service also checks roles, but it reports a mismatch as a 409. A 403 on its own
already means the route-level check fired; these tests go further and make the route
body explode if it's ever reached, proving the request never got that far.
"""

import pytest

import app.routers.clubs as clubs_router
import app.routers.requirements as requirements_router
from tests.conftest import auth, create_club, provide_all_documents

ADMIN_ROUTES = [
    ("start-review", None),
    ("request-changes", {"note": "fix it"}),
    ("reject", {"note": "no"}),
    ("approve", None),
    ("requirements/budget/approve", None),
    ("requirements/budget/reject", {"note": "no"}),
]


def _must_not_run(*args, **kwargs):
    raise AssertionError("route body ran for a caller who should have been stopped")


@pytest.fixture
def body_must_not_run(monkeypatch):
    monkeypatch.setattr(clubs_router, "get_club_or_404", _must_not_run)
    monkeypatch.setattr(clubs_router, "attempt_transition", _must_not_run)
    monkeypatch.setattr(requirements_router, "get_club_or_404", _must_not_run)


@pytest.mark.parametrize(("action", "body"), ADMIN_ROUTES)
def test_club_lead_stopped_before_route_body(client, lead, body_must_not_run, action, body):
    # Club id doesn't even need to exist: the role check comes before any lookup.
    response = client.post(f"/clubs/1/{action}", json=body, headers=auth(lead))
    assert response.status_code == 403


@pytest.mark.parametrize(("action", "body"), ADMIN_ROUTES)
def test_unauthenticated_stopped_before_route_body(client, body_must_not_run, action, body):
    assert client.post(f"/clubs/1/{action}", json=body).status_code == 401


def test_resubmit_not_admin_gated(client, db, lead, admin):
    club = create_club(client, lead)
    provide_all_documents(db, club["id"])
    for action, user, body in [
        ("submit", lead, None),
        ("start-review", admin, None),
        ("request-changes", admin, {"note": "fix it"}),
        ("resubmit", lead, None),
    ]:
        response = client.post(f"/clubs/{club['id']}/{action}", json=body, headers=auth(user))
        assert response.status_code == 200, (action, response.text)
    assert response.json()["status"] == "submitted"
