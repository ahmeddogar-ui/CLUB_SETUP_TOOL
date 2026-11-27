"""generalise club_events into events: comments, role changes, activity log

Revision ID: 2b8d4f6a1c30
Revises: 1a7c3e5b9d20
Create Date: 2026-11-26 00:00:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2b8d4f6a1c30"
down_revision: str | Sequence[str] | None = "1a7c3e5b9d20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APPEND_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION {name}() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '{table} is append-only: % is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql
"""


def upgrade() -> None:
    # One history for the whole app: the same append-only table now also holds
    # comments and role changes, which the admin's activity log reads.
    op.rename_table("club_events", "events")
    op.execute("ALTER TABLE events RENAME CONSTRAINT pk_club_events TO pk_events")
    for column in ("actor_id", "club_id", "requirement_id"):
        op.execute(
            f"ALTER TABLE events RENAME CONSTRAINT fk_club_events_{column} "
            f"TO fk_events_{column}"
        )
    op.execute("ALTER SEQUENCE club_events_id_seq RENAME TO events_id_seq")
    op.execute(
        "ALTER TRIGGER club_events_append_only ON events RENAME TO events_append_only"
    )
    op.execute("ALTER FUNCTION club_events_append_only() RENAME TO events_append_only")
    op.execute(APPEND_ONLY_FUNCTION.format(name="events_append_only", table="events"))

    # A role change is about a user, not a club, and moves no club status.
    op.alter_column("events", "club_id", nullable=True)
    op.alter_column("events", "to_status", nullable=True)
    op.add_column("events", sa.Column("subject_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_events_subject_user_id", "events", "users", ["subject_user_id"], ["id"]
    )
    op.create_check_constraint(
        op.f("ck_events_about_club_or_user"),
        "events",
        "club_id IS NOT NULL OR subject_user_id IS NOT NULL",
    )

    # The activity log: newest first overall, by actor, and by type.
    op.create_index(
        "idx_events_time", "events", [sa.text("created_at DESC"), sa.text("id DESC")]
    )
    op.create_index(
        "idx_events_actor_time", "events", ["actor_id", sa.text("created_at DESC")]
    )
    op.create_index(
        "idx_events_type_time", "events", ["event_type", sa.text("created_at DESC")]
    )


def downgrade() -> None:
    op.drop_index("idx_events_type_time", table_name="events")
    op.drop_index("idx_events_actor_time", table_name="events")
    op.drop_index("idx_events_time", table_name="events")
    op.drop_constraint(op.f("ck_events_about_club_or_user"), "events", type_="check")
    op.drop_constraint("fk_events_subject_user_id", "events", type_="foreignkey")
    op.drop_column("events", "subject_user_id")
    op.alter_column("events", "to_status", nullable=False)
    op.alter_column("events", "club_id", nullable=False)
    op.execute("ALTER FUNCTION events_append_only() RENAME TO club_events_append_only")
    op.execute(
        APPEND_ONLY_FUNCTION.format(name="club_events_append_only", table="club_events")
    )
    op.execute(
        "ALTER TRIGGER events_append_only ON events RENAME TO club_events_append_only"
    )
    op.execute("ALTER SEQUENCE events_id_seq RENAME TO club_events_id_seq")
    for column in ("actor_id", "club_id", "requirement_id"):
        op.execute(
            f"ALTER TABLE events RENAME CONSTRAINT fk_events_{column} "
            f"TO fk_club_events_{column}"
        )
    op.execute("ALTER TABLE events RENAME CONSTRAINT pk_events TO pk_club_events")
    op.rename_table("events", "club_events")
