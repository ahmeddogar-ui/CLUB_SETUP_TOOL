from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app

# Nothing listens on port 1, so connecting fails the way a down database does.
UNREACHABLE_DATABASE_URL = "postgresql://localhost:1/unreachable"


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dbhealth_is_ok(client):
    response = client.get("/dbhealth")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dbhealth_is_503_when_the_database_is_unreachable(client):
    engine = create_engine(UNREACHABLE_DATABASE_URL)
    session = Session(engine)
    app.dependency_overrides[get_db] = lambda: session
    try:
        response = client.get("/dbhealth")
    finally:
        session.close()
        engine.dispose()
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
