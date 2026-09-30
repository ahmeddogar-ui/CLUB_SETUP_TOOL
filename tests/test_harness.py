"""Ticket 25: prove the test harness itself is trustworthy before anything else
gets built on top of it.

These tests exist to fail loudly if the rollback fixture in conftest.py ever
stops working -- e.g. if `db` starts committing to the real transaction
instead of a savepoint, every other test file would start leaking rows into
the test database without any single test necessarily noticing.
"""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import TEST_DATABASE_URL, make_user


def test_row_is_visible_during_the_test_then_gone_after_rollback(engine):
    """Simulates exactly what the `db` fixture does (open connection, begin
    transaction, session-as-savepoint, insert, rollback, close) inline in one
    test, so we can assert on both sides of the rollback ourselves instead of
    trusting the fixture's teardown blindly.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    user = make_user(session)  # calls session.commit(), which only releases a savepoint
    user_id = user.id

    # Mid-test: the row is there on this session.
    assert session.get(User, user_id) is not None

    # Simulate the fixture's teardown.
    session.close()
    transaction.rollback()
    connection.close()

    # After "the test finishes": query the real test database on a brand new
    # connection. If the row survived, the outer transaction was committed
    # somewhere instead of rolled back, and the harness can't be trusted.
    with engine.connect() as check_connection:
        found = check_connection.execute(
            select(User).where(User.id == user_id)
        ).first()
    assert found is None


def test_a_committed_row_is_invisible_to_a_completely_separate_connection(db, lead):
    """Same proof, but through the real `db`/fixtures tests actually use, and
    checked against a fully independent connection (its own engine, not just
    another connection off the shared one) -- the same isolation another
    test's session would see if the rollback fixture were broken.
    """
    assert lead.id is not None  # `lead` already went through db.commit()

    outside_engine = create_engine(TEST_DATABASE_URL)
    try:
        with outside_engine.connect() as outside_connection:
            found = outside_connection.execute(
                select(User).where(User.id == lead.id)
            ).first()
        assert found is None
    finally:
        outside_engine.dispose()
