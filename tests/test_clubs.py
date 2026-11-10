"""Club create / detail / update endpoints (POST /clubs, GET and PATCH /clubs/{id})."""

import pytest

from app.models import ClubEvent, Clubs, ClubStatus, Requirement
from app.services.clubs import INITIAL_REQUIREMENTS
from tests.conftest import auth, create_club, make_club

CLUB_OUT_FIELDS = {"id", "name", "description", "status", "submitter_id"}
NOT_EDITABLE = [
    status
    for status in ClubStatus
    if status not in (ClubStatus.drafting, ClubStatus.changes_requested)
]


# --- create ---------------------------------------------------------------------


@pytest.mark.parametrize("missing", ["name", "description"])
def test_create_missing_field_is_422(client, lead, missing):
    body = {"name": "Chess Club", "description": "We play chess"}
    del body[missing]
    assert client.post("/clubs", json=body, headers=auth(lead)).status_code == 422


def test_create_requires_authentication(client):
    response = client.post("/clubs", json={"name": "Chess", "description": "Chess"})
    assert response.status_code == 401


def test_create_starts_drafting_owned_by_caller_with_club_out_shape(client, lead):
    club = create_club(client, lead)

    assert set(club) == CLUB_OUT_FIELDS
    assert club["status"] == "drafting"
    assert club["submitter_id"] == lead.id


def test_create_writes_full_requirement_set_and_one_created_event(client, db, lead):
    club = create_club(client, lead)

    requirements = db.query(Requirement).filter(Requirement.club_id == club["id"]).all()
    assert sorted((r.requirement_type, r.kind) for r in requirements) == sorted(
        INITIAL_REQUIREMENTS
    )
    assert all(r.status.value == "pending" and r.link_url is None for r in requirements)

    events = db.query(ClubEvent).filter(ClubEvent.club_id == club["id"]).all()
    assert [(e.event_type, e.from_status, e.to_status, e.actor_id) for e in events] == [
        ("created", None, ClubStatus.drafting, lead.id)
    ]


def test_two_clubs_get_independent_requirement_rows(client, db, lead):
    first = create_club(client, lead, name="Chess")
    second = create_club(client, lead, name="Go")

    def requirement_ids(club_id):
        return {
            r.id for r in db.query(Requirement).filter(Requirement.club_id == club_id)
        }

    first_ids, second_ids = requirement_ids(first["id"]), requirement_ids(second["id"])
    assert len(first_ids) == len(second_ids) == len(INITIAL_REQUIREMENTS)
    assert first_ids.isdisjoint(second_ids)


# --- detail ---------------------------------------------------------------------


@pytest.mark.parametrize("viewer", ["lead", "admin"])
def test_owner_and_admin_can_read_detail(client, request, lead, viewer):
    club = create_club(client, lead)
    user = request.getfixturevalue(viewer)

    response = client.get(f"/clubs/{club['id']}", headers=auth(user))

    assert response.status_code == 200
    assert response.json() == club


def test_other_lead_gets_403_without_any_club_data(client, lead, other_lead):
    club = create_club(client, lead, name="Secret Society", description="Hidden agenda")

    response = client.get(f"/clubs/{club['id']}", headers=auth(other_lead))

    assert response.status_code == 403
    assert "Secret Society" not in response.text
    assert "Hidden agenda" not in response.text


def test_missing_club_is_404_even_for_a_non_owner(client, lead):
    # Existence is checked before ownership, so a 404 never hints at someone else's id.
    assert client.get("/clubs/999999", headers=auth(lead)).status_code == 404


# --- update ---------------------------------------------------------------------


def patch(client, club_id, user, body):
    return client.patch(f"/clubs/{club_id}", json=body, headers=auth(user))


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"name": "Go Club"}, ("Go Club", "We play chess")),
        ({"description": "We play go"}, ("Chess Club", "We play go")),
        ({"name": "Go Club", "description": "We play go"}, ("Go Club", "We play go")),
        ({}, ("Chess Club", "We play chess")),
    ],
)
def test_update_changes_only_the_fields_sent(client, db, lead, body, expected):
    club = make_club(db, lead)

    response = patch(client, club.id, lead, body)

    assert response.status_code == 200
    db.refresh(club)
    assert (club.name, club.description) == expected
    assert (response.json()["name"], response.json()["description"]) == expected


def test_update_allowed_while_changes_requested(client, db, lead):
    club = make_club(db, lead, status=ClubStatus.changes_requested)
    assert patch(client, club.id, lead, {"name": "Renamed"}).status_code == 200


@pytest.mark.parametrize("status", NOT_EDITABLE)
def test_update_after_submission_is_409_and_changes_nothing(client, db, lead, status):
    club = make_club(db, lead, status=status)

    response = patch(client, club.id, lead, {"name": "Sneaky rename"})

    assert response.status_code == 409
    db.expire_all()
    assert db.get(Clubs, club.id).name == "Chess Club"


def test_update_someone_elses_club_is_403_before_the_status_check(client, db, lead, other_lead):
    # A submitted club would be a 409 for its owner; a stranger must see 403 instead.
    club = make_club(db, lead, status=ClubStatus.submitted)

    response = patch(client, club.id, other_lead, {"name": "Hijacked"})

    assert response.status_code == 403
    db.expire_all()
    assert db.get(Clubs, club.id).name == "Chess Club"


def test_update_missing_club_is_404(client, lead):
    assert patch(client, 999999, lead, {"name": "Ghost"}).status_code == 404


def test_update_requires_authentication(client, db, lead):
    club = make_club(db, lead)
    assert client.patch(f"/clubs/{club.id}", json={"name": "Anon"}).status_code == 401
