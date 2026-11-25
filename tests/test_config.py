import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_SECRET = "a" * 32


def make_settings(**overrides):
    values = {"DATABASE_URL": "postgresql://localhost/db", "SECRET_KEY": VALID_SECRET}
    # _env_file=None: read only what the test passes, never the developer's .env.
    return Settings(_env_file=None, **(values | overrides))


def test_secret_key_shorter_than_32_characters_is_refused():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make_settings(SECRET_KEY="a" * 31)


def test_postgres_scheme_is_normalised_for_sqlalchemy():
    settings = make_settings(DATABASE_URL="postgres://user:pw@host:5432/db")
    assert settings.DATABASE_URL == "postgresql://user:pw@host:5432/db"


def test_api_docs_are_off_unless_enabled():
    assert make_settings().ENABLE_API_DOCS is False


def test_api_docs_are_not_served_by_default(client):
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404
