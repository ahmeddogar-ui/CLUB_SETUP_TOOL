"""Ticket 26: auth edge cases from edge-case-checklist.md's Register/Login/
Protected-routes sections. Wrong-role-vs-right-role on `require_role` itself is
already covered by test_admin_route_guards.py (ticket 23) and isn't repeated here.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.models import User
from tests.conftest import auth, make_user


def register(client, name="Ada", email="ada@example.com", password="hunter2"):
    return client.post("/auth/register", json={"name": name, "email": email, "password": password})


def login(client, email, password):
    # /auth/login is OAuth2PasswordRequestForm -- form-encoded, not JSON.
    return client.post("/auth/login", data={"username": email, "password": password})


def expired_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# --- register ----------------------------------------------------------------


def test_register_missing_field_is_422(client):
    response = client.post("/auth/register", json={"name": "Ada", "email": "ada@example.com"})
    assert response.status_code == 422


def test_register_duplicate_email_is_409_not_500(client, db):
    first = register(client, email="dupe@example.com")
    assert first.status_code == 201, first.text

    second = register(client, name="Someone Else", email="dupe@example.com")
    assert second.status_code == 409

    count = db.query(User).filter(User.email == "dupe@example.com").count()
    assert count == 1


def test_register_response_has_no_password_fields(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert set(body.keys()) == {"id", "name", "email", "role"}


def test_register_hashes_password_and_defaults_role(client, db):
    response = register(client, password="plaintext-password")
    user = db.query(User).filter(User.email == "ada@example.com").first()

    assert user.password_hash != "plaintext-password"
    assert "plaintext-password" not in user.password_hash
    assert user.role.value == "club_lead"


# --- login ---------------------------------------------------------------------


def test_login_correct_credentials_returns_bearer_token(client):
    register(client, email="ada@example.com", password="hunter2")

    response = login(client, "ada@example.com", "hunter2")

    assert response.status_code == 200
    assert response.json() == {
        "access_token": response.json()["access_token"],
        "token_type": "bearer",
    }
    assert response.json()["access_token"]  # non-empty


def test_login_wrong_password_is_401_generic(client):
    register(client, email="ada@example.com", password="hunter2")

    response = login(client, "ada@example.com", "wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_email_is_same_generic_401(client):
    response = login(client, "nobody@example.com", "whatever")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_email_matching_is_consistent_by_case(client):
    """Current behavior: email matching is a plain equality check on the
    stored value (no case-folding), so a different-case login is treated as a
    different, nonexistent user -- consistently 401, never a silent partial
    match.

    Domain kept lowercase throughout deliberately: EmailStr (via
    email-validator) normalizes the *domain* to lowercase on register --
    local part is left as-is -- so a mixed-case domain here would be
    comparing against a value that was silently rewritten on the way in,
    which is a different behavior than the local-part case-sensitivity this
    test is actually after.
    """
    register(client, email="Ada@example.com", password="hunter2")

    same_case = login(client, "Ada@example.com", "hunter2")
    different_case = login(client, "ada@example.com", "hunter2")

    assert same_case.status_code == 200
    assert different_case.status_code == 401
    assert different_case.json()["detail"] == "Incorrect email or password"


# --- protected routes / get_current_user ---------------------------------------


def test_valid_token_resolves_the_right_user(client, lead):
    response = client.get("/auth/me", headers=auth(lead))

    assert response.status_code == 200
    assert response.json()["id"] == lead.id
    assert response.json()["email"] == lead.email


def test_missing_auth_header_is_401(client):
    assert client.get("/auth/me").status_code == 401


def test_malformed_token_is_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_tampered_token_is_401(client, lead):
    token = auth(lead)["Authorization"].split(" ")[1]
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401


def test_expired_token_is_401(client, lead):
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {expired_token(lead.id)}"}
    )
    assert response.status_code == 401


def test_discarding_the_token_client_side_is_equivalent_to_no_token(client):
    """Access tokens are stateless JWTs with no server-side revocation (a
    deliberate scope cut -- see PLAN.md). "Logout" is a client-side action
    only: the token itself stays valid until it expires, so the only thing
    to confirm is that a request sent *without* it is rejected the same way
    an unauthenticated request always is.
    """
    assert client.get("/auth/me").status_code == 401


# --- require_role (success path only; the 403 path is ticket 23's) ------------


def test_admin_role_user_passes_require_role(client, admin, db):
    from tests.conftest import create_club

    club = create_club(client, admin)
    response = client.post(f"/clubs/{club['id']}/start-review", headers=auth(admin))
    # Not a legal transition from `drafting`, but a 409 proves require_role let it
    # through to the transition service -- a 403 here would mean the role check
    # itself rejected a genuine admin, which is the thing this test guards against.
    assert response.status_code == 409
