import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent

# Point the app at the test database before anything imports app.core.config.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise pytest.UsageError(
        "Set TEST_DATABASE_URL to a dedicated, disposable Postgres database "
        "(e.g. postgresql://user:password@db-host:5432/club_setup_tool_test)."
    )

# Refuse to run against the dev database. Read the dev URL the same way the app
# does (env var first, then .env), and do it before DATABASE_URL is overwritten below.
_dev_url = os.environ.get("DATABASE_URL") or dotenv_values(ROOT / ".env").get("DATABASE_URL")
_test_url = make_url(TEST_DATABASE_URL)
if _dev_url:
    _dev = make_url(_dev_url)
    if (_test_url.host, _test_url.port, _test_url.database) == (
        _dev.host,
        _dev.port,
        _dev.database,
    ):
        raise pytest.UsageError(
            f"TEST_DATABASE_URL points at the dev database ({_dev.database!r} on "
            f"{_dev.host!r}). Tests roll back, but migrations and any leaked commit "
            "would still hit real data."
        )
# The dev and test databases can live on the same remote server, reachable under
# different hostnames/IPs the check above can't see through -- so also require the
# database name itself to say it's a test database.
if "test" not in (_test_url.database or ""):
    raise pytest.UsageError(
        f"Test database name {_test_url.database!r} must contain 'test' so it "
        "can't be mistaken for the dev database."
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    ClubEvent,
    Clubs,
    ClubStatus,
    Requirement,
    RequirementKind,
    RequirementStatus,
    User,
    UserRole,
)
from app.routers.clubs import INITIAL_REQUIREMENTS  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    # Run the real migrations so the test schema (enums, triggers) matches production.
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")

    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    # Every test runs inside one outer transaction that is rolled back at the end.
    # Code under test still calls commit(); those only release a savepoint.
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


_user_counter = 0


def make_user(db: Session, role: UserRole = UserRole.club_lead) -> User:
    global _user_counter
    _user_counter += 1
    user = User(
        name=f"{role.value} {_user_counter}",
        email=f"{role.value}{_user_counter}@example.com",
        password_hash=hash_password("password"),
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def lead(db):
    return make_user(db, UserRole.club_lead)


@pytest.fixture
def other_lead(db):
    return make_user(db, UserRole.club_lead)


@pytest.fixture
def admin(db):
    return make_user(db, UserRole.admin)


def create_club(client, user: User, name="Chess Club", description="We play chess"):
    response = client.post(
        "/clubs", json={"name": name, "description": description}, headers=auth(user)
    )
    assert response.status_code == 201, response.text
    return response.json()


def requirements_for(db: Session, club_id: int) -> dict[str, Requirement]:
    rows = db.query(Requirement).filter(Requirement.club_id == club_id).all()
    return {row.requirement_type.value: row for row in rows}


def provide_all_documents(db: Session, club_id: int) -> None:
    for requirement in requirements_for(db, club_id).values():
        if requirement.kind == RequirementKind.document:
            requirement.link_url = f"https://example.com/{requirement.requirement_type.value}"
            requirement.status = RequirementStatus.submitted
    db.commit()


def approve_all_requirements(db: Session, club_id: int) -> None:
    for requirement in requirements_for(db, club_id).values():
        requirement.status = RequirementStatus.approved
    db.commit()


def make_club(
    db: Session,
    owner: User,
    status: ClubStatus = ClubStatus.drafting,
    requirement_status: RequirementStatus | None = None,
    name: str = "Chess Club",
    description: str = "We play chess",
) -> Clubs:
    """Build a club directly at rest in `status`, skipping the API calls and
    guard checks it would normally take to walk there (submit, start-review, ...).

    `requirement_status`, if given, is applied to every requirement (document
    and checklist alike) -- e.g. RequirementStatus.approved for a club that's
    ready to be approved, or RequirementStatus.submitted for one mid-review.
    Leave it None to keep the default `pending` on every requirement.

    This writes rows straight into the DB and does not emit ClubEvent rows for
    the skipped transitions -- it is not a substitute for tests that exercise
    the transition endpoints themselves, only for tests that need a club
    already sitting in some state to test something else.
    """
    club = Clubs(
        name=name,
        description=description,
        submitter_id=owner.id,
        status=status,
    )
    db.add(club)
    db.flush()

    for requirement_type, kind in INITIAL_REQUIREMENTS:
        db.add(
            Requirement(
                club_id=club.id,
                requirement_type=requirement_type,
                kind=kind,
                status=requirement_status or RequirementStatus.pending,
                link_url=(
                    f"https://example.com/{requirement_type.value}"
                    if requirement_status and kind == RequirementKind.document
                    else None
                ),
            )
        )

    db.add(
        ClubEvent(
            club_id=club.id,
            actor_id=owner.id,
            event_type="created",
            from_status=None,
            to_status=status,
        )
    )

    db.commit()
    db.refresh(club)
    return club
