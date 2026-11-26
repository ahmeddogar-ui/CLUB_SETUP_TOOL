from app.core.security import verify_password
from app.models import RefreshToken, User
from tests.conftest import auth

ME_URL = "/api/auth/me"
PASSWORD_URL = "/api/auth/me/password"
NEW_PASSWORD = "a-new-password"


def log_in(client, user: User, password: str = "password"):
    return client.post(
        "/api/auth/login", data={"username": user.email, "password": password}
    )


def change_password(client, user: User, current: str, new: str):
    return client.post(
        PASSWORD_URL,
        json={"current_password": current, "new_password": new},
        headers=auth(user),
    )


class TestRename:
    def test_updates_and_trims_the_name(self, client, lead):
        response = client.patch(
            ME_URL, json={"name": "  Ada Lovelace  "}, headers=auth(lead)
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Ada Lovelace"
        assert client.get(ME_URL, headers=auth(lead)).json()["name"] == "Ada Lovelace"

    def test_rejects_a_blank_name(self, client, lead):
        response = client.patch(ME_URL, json={"name": "   "}, headers=auth(lead))

        assert response.status_code == 422

    def test_requires_authentication(self, client):
        response = client.patch(ME_URL, json={"name": "Ada"})

        assert response.status_code == 401


class TestChangePassword:
    def test_wrong_current_password_is_forbidden_and_changes_nothing(
        self, client, db, lead
    ):
        old_hash = lead.password_hash

        response = change_password(client, lead, "not-my-password", NEW_PASSWORD)

        assert response.status_code == 403
        assert response.json()["detail"] == "Current password is incorrect"
        db.refresh(lead)
        assert lead.password_hash == old_hash

    def test_rejects_a_too_short_new_password(self, client, lead):
        response = change_password(client, lead, "password", "short")

        assert response.status_code == 422

    def test_requires_authentication(self, client):
        response = client.post(
            PASSWORD_URL,
            json={"current_password": "password", "new_password": NEW_PASSWORD},
        )

        assert response.status_code == 401

    def test_new_password_signs_in_and_the_old_one_does_not(self, client, db, lead):
        response = change_password(client, lead, "password", NEW_PASSWORD)

        assert response.status_code == 204
        db.refresh(lead)
        assert verify_password(NEW_PASSWORD, lead.password_hash)
        assert log_in(client, lead, NEW_PASSWORD).status_code == 200
        assert log_in(client, lead, "password").status_code == 401

    def test_revokes_other_sessions_but_keeps_the_current_one(self, client, db, lead):
        log_in(client, lead)
        other_session_cookie = client.cookies["refresh_token"]
        log_in(client, lead)
        current_session_cookie = client.cookies["refresh_token"]
        assert other_session_cookie != current_session_cookie

        response = change_password(client, lead, "password", NEW_PASSWORD)

        assert response.status_code == 204
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == lead.id).all()
        assert len(tokens) == 2
        assert sorted(token.revoked_at is None for token in tokens) == [False, True]
        client.cookies.set("refresh_token", other_session_cookie)
        assert client.post("/api/auth/refresh").status_code == 401
        client.cookies.set("refresh_token", current_session_cookie)
        assert client.post("/api/auth/refresh").status_code == 200
