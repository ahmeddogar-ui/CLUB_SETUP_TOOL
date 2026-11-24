"""Refresh tokens: the edge-case checklist's "Refresh tokens" section."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import hash_refresh_token, new_refresh_token
from app.models import RefreshToken
from app.routers.auth import REFRESH_COOKIE


def login(client, user):
    response = client.post(
        "/auth/login", data={"username": user.email, "password": "password"}
    )
    assert response.status_code == 200, response.text
    return response


def stored_tokens(db, user):
    return db.query(RefreshToken).filter(RefreshToken.user_id == user.id).all()


def store_token(db, user, **overrides):
    """A refresh token row in a chosen state; returns the raw cookie value."""
    raw = new_refresh_token()
    fields = {
        "user_id": user.id,
        "token_hash": hash_refresh_token(raw),
        "expires_at": datetime.now(UTC) + timedelta(days=1),
        **overrides,
    }
    db.add(RefreshToken(**fields))
    db.commit()
    return raw


def refresh(client, cookie=None):
    if cookie is not None:
        client.cookies.set(REFRESH_COOKIE, cookie)
    return client.post("/auth/refresh")


def test_login_sets_refresh_token_as_httponly_cookie_not_in_body(client, db, lead):
    response = login(client, lead)

    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{REFRESH_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert set(response.json()) == {"access_token", "token_type"}
    assert response.cookies[REFRESH_COOKIE] not in response.text

    # Stored hashed, never as the raw value.
    [row] = stored_tokens(db, lead)
    assert row.token_hash == hash_refresh_token(response.cookies[REFRESH_COOKIE])


def test_valid_cookie_returns_a_working_access_token(client, lead):
    login(client, lead)

    response = refresh(client)

    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["id"] == lead.id


@pytest.mark.parametrize(
    "state",
    [
        {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
        {"revoked_at": datetime.now(UTC)},
    ],
    ids=["expired", "revoked"],
)
def test_expired_or_revoked_cookie_is_401(client, db, lead, state):
    assert refresh(client, store_token(db, lead, **state)).status_code == 401


def test_unknown_cookie_is_401(client):
    assert refresh(client, "not-a-real-token").status_code == 401


def test_no_cookie_is_401(client):
    assert refresh(client).status_code == 401


def test_logout_revokes_the_token_and_clears_the_cookie(client, db, lead):
    cookie = login(client, lead).cookies[REFRESH_COOKIE]

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert REFRESH_COOKIE not in client.cookies
    [row] = stored_tokens(db, lead)
    db.refresh(row)
    assert row.revoked_at is not None
    assert refresh(client, cookie).status_code == 401


def test_logout_only_revokes_that_session(client, db, lead):
    other_session = store_token(db, lead)
    login(client, lead)

    client.post("/auth/logout")

    assert refresh(client, other_session).status_code == 200


def test_logout_without_a_cookie_is_harmless(client):
    assert client.post("/auth/logout").status_code == 204
