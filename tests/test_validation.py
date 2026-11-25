"""Length limits on every client-supplied string, so no request can store an
unbounded value."""

import pytest

from app.models import ClubStatus, RequirementStatus
from app.schemas import (
    CLUB_NAME_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    NOTE_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PERSON_NAME_MAX_LENGTH,
    URL_MAX_LENGTH,
)
from tests.conftest import auth, make_club

URL_PREFIX = "https://docs.example.com/"


def register(client, name="Ada", password="a-good-password"):
    return client.post(
        "/auth/register",
        json={"name": name, "email": "ada@example.com", "password": password},
    )


def url_of_length(length: int) -> str:
    return URL_PREFIX + "a" * (length - len(URL_PREFIX))


# --- register -----------------------------------------------------------------


def test_password_shorter_than_the_minimum_is_422(client):
    response = register(client, password="a" * (PASSWORD_MIN_LENGTH - 1))
    assert response.status_code == 422


def test_password_at_the_minimum_is_accepted(client):
    response = register(client, password="a" * PASSWORD_MIN_LENGTH)
    assert response.status_code == 201


def test_password_longer_than_the_maximum_is_422(client):
    response = register(client, password="a" * (PASSWORD_MAX_LENGTH + 1))
    assert response.status_code == 422


def test_person_name_longer_than_the_maximum_is_422(client):
    response = register(client, name="a" * (PERSON_NAME_MAX_LENGTH + 1))
    assert response.status_code == 422


def test_person_name_at_the_maximum_is_accepted(client):
    response = register(client, name="a" * PERSON_NAME_MAX_LENGTH)
    assert response.status_code == 201


def test_blank_person_name_is_422(client):
    assert register(client, name="   ").status_code == 422


# --- clubs ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "max_length"),
    [("name", CLUB_NAME_MAX_LENGTH), ("description", DESCRIPTION_MAX_LENGTH)],
)
def test_club_fields_over_the_maximum_are_422_on_create(
    client, lead, field, max_length
):
    body = {"name": "Chess", "description": "We play", field: "a" * (max_length + 1)}
    response = client.post("/clubs", json=body, headers=auth(lead))
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "max_length"),
    [("name", CLUB_NAME_MAX_LENGTH), ("description", DESCRIPTION_MAX_LENGTH)],
)
def test_club_fields_at_the_maximum_are_accepted_on_create(
    client, lead, field, max_length
):
    body = {"name": "Chess", "description": "We play", field: "a" * max_length}
    response = client.post("/clubs", json=body, headers=auth(lead))
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("field", "max_length"),
    [("name", CLUB_NAME_MAX_LENGTH), ("description", DESCRIPTION_MAX_LENGTH)],
)
def test_club_fields_over_the_maximum_are_422_on_update(
    client, db, lead, field, max_length
):
    club = make_club(db, lead)
    response = client.patch(
        f"/clubs/{club.id}", json={field: "a" * (max_length + 1)}, headers=auth(lead)
    )
    assert response.status_code == 422


# --- review notes -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "request-changes",
        "reject",
        "requirements/budget/approve",
        "requirements/budget/reject",
    ],
)
def test_note_over_the_maximum_is_422(client, db, lead, admin, path):
    club = make_club(
        db,
        lead,
        status=ClubStatus.under_review,
        requirement_status=RequirementStatus.submitted,
    )
    response = client.post(
        f"/clubs/{club.id}/{path}",
        json={"note": "a" * (NOTE_MAX_LENGTH + 1)},
        headers=auth(admin),
    )
    assert response.status_code == 422


def test_note_at_the_maximum_is_accepted(client, db, lead, admin):
    club = make_club(
        db,
        lead,
        status=ClubStatus.under_review,
        requirement_status=RequirementStatus.submitted,
    )
    response = client.post(
        f"/clubs/{club.id}/reject",
        json={"note": "a" * NOTE_MAX_LENGTH},
        headers=auth(admin),
    )
    assert response.status_code == 200


# --- requirement links --------------------------------------------------------------


def test_link_over_the_maximum_is_422(client, db, lead):
    club = make_club(db, lead)
    response = client.put(
        f"/clubs/{club.id}/requirements/budget/link",
        json={"link_url": url_of_length(URL_MAX_LENGTH + 1)},
        headers=auth(lead),
    )
    assert response.status_code == 422


def test_link_at_the_maximum_is_accepted(client, db, lead):
    club = make_club(db, lead)
    response = client.put(
        f"/clubs/{club.id}/requirements/budget/link",
        json={"link_url": url_of_length(URL_MAX_LENGTH)},
        headers=auth(lead),
    )
    assert response.status_code == 200
