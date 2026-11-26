"""Admin user management: GET /users and PATCH /users/{id}/role."""

from sqlalchemy import select

from app.models import Event, User, UserRole
from tests.conftest import auth, make_club, make_user


def list_users(client, admin, **params):
    response = client.get("/api/users", params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return response.json()


def change_role(client, admin, user_id, role):
    return client.patch(
        f"/api/users/{user_id}/role", json={"role": role}, headers=auth(admin)
    )


def test_admin_searches_users_by_name_or_email(client, db, admin):
    ada = make_user(db)
    ada.name = "Ada Lovelace"
    grace = make_user(db)
    grace.email = "grace.hopper@example.com"
    db.commit()

    by_name = list_users(client, admin, q="lovelace")
    by_email = list_users(client, admin, q="GRACE.HOP")

    assert [user["id"] for user in by_name["items"]] == [ada.id]
    assert [user["id"] for user in by_email["items"]] == [grace.id]
    assert set(by_name["items"][0]) == {"id", "name", "email", "role", "created_at"}


def test_admin_filters_users_by_role_and_pages(client, db, admin):
    leads = [make_user(db) for _ in range(3)]

    page = list_users(client, admin, role="club_lead", limit=2, offset=0)

    assert page["total"] >= 3
    assert len(page["items"]) == 2
    assert {user["role"] for user in page["items"]} == {"club_lead"}
    # Sorted by name, then id: a stable order for paging.
    everyone = list_users(client, admin, role="club_lead", limit=100)["items"]
    ours = [user["id"] for user in everyone if user["id"] in {u.id for u in leads}]
    assert ours == sorted(
        ours, key=lambda user_id: (db.get(User, user_id).name.lower(), user_id)
    )


def test_non_admin_cannot_list_or_change_users(client, lead, other_lead):
    assert client.get("/api/users", headers=auth(lead)).status_code == 403
    assert change_role(client, lead, other_lead.id, "admin").status_code == 403


def test_admin_changes_a_role_and_it_is_recorded(client, db, admin, lead):
    response = change_role(client, admin, lead.id, "admin")

    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"
    db.refresh(lead)
    assert lead.role == UserRole.admin
    [event] = db.scalars(select(Event).where(Event.subject_user_id == lead.id)).all()
    assert event.event_type == "role_changed"
    assert event.actor_id == admin.id
    assert event.club_id is None
    assert event.note == "Club lead → Admin"


def test_setting_the_same_role_changes_nothing(client, db, admin, lead):
    assert change_role(client, admin, lead.id, "club_lead").status_code == 200
    assert db.scalars(select(Event).where(Event.subject_user_id == lead.id)).all() == []


def test_admin_cannot_change_own_role(client, db, admin):
    response = change_role(client, admin, admin.id, "club_lead")

    assert response.status_code == 409
    assert "your own role" in response.json()["detail"]
    db.refresh(admin)
    assert admin.role == UserRole.admin


def test_lead_who_owns_clubs_keeps_the_club_lead_role(client, db, admin, lead):
    make_club(db, lead)

    response = change_role(client, admin, lead.id, "admin")

    assert response.status_code == 409
    assert "owns clubs" in response.json()["detail"]
    db.refresh(lead)
    assert lead.role == UserRole.club_lead


def test_unknown_user_is_404_and_unknown_role_422(client, admin, lead):
    assert change_role(client, admin, 999_999, "admin").status_code == 404
    assert change_role(client, admin, lead.id, "superuser").status_code == 422
