"""add requests: rooms, funding line items, approvals, the finance role

Revision ID: 3c9e5a7b2d41
Revises: 2b8d4f6a1c30
Create Date: 2026-11-26 00:00:02.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3c9e5a7b2d41"
down_revision: str | Sequence[str] | None = "2b8d4f6a1c30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The finance step of funding requests. Not used in this transaction, which
    # Postgres requires of a value added here.
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'finance_approver'")
    # Lets one GiST index combine room_id (=) with the time range (&&).
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("building", sa.String(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rooms")),
        sa.UniqueConstraint("name", name=op.f("uq_rooms_name")),
    )
    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column(
            "request_type",
            sa.Enum("funding", "room_booking", name="request_type_kind"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "submitted",
                "in_review",
                "changes_requested",
                "approved",
                "rejected",
                "cancelled",
                name="requeststatus",
            ),
            nullable=False,
        ),
        sa.Column("round", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "awaiting_role",
            postgresql.ENUM(name="userrole", create_type=False),
            nullable=True,
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("booked_during", postgresql.TSTZRANGE(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        postgresql.ExcludeConstraint(
            (sa.column("room_id"), "="),
            (sa.column("booked_during"), "&&"),
            where=sa.text(
                "status IN ('submitted', 'in_review', 'changes_requested', 'approved')"
            ),
            using="gist",
            name="no_double_booking",
        ),
        sa.CheckConstraint(
            "(awaiting_role IS NOT NULL) = (status IN ('submitted', 'in_review'))",
            name=op.f("ck_requests_awaiting_role_matches_status"),
        ),
        sa.CheckConstraint(
            "(request_type = 'room_booking') = (room_id IS NOT NULL AND booked_during IS NOT NULL)",
            name=op.f("ck_requests_booking_fields_match_type"),
        ),
        sa.CheckConstraint(
            "NOT isempty(booked_during)", name=op.f("ck_requests_booking_not_empty")
        ),
        sa.ForeignKeyConstraint(
            ["club_id"],
            ["clubs.id"],
            name=op.f("fk_requests_club_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], name=op.f("fk_requests_created_by_id")
        ),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name=op.f("fk_requests_room_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requests")),
    )
    op.create_index(
        "idx_requests_awaiting_updated",
        "requests",
        ["awaiting_role", "updated_at"],
        unique=False,
    )
    op.create_index(
        "idx_requests_club_updated", "requests", ["club_id", "updated_at"], unique=False
    )
    op.create_table(
        "funding_line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "amount_cents > 0", name=op.f("ck_funding_line_items_amount_positive")
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            name=op.f("fk_funding_line_items_request_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_funding_line_items")),
        sa.UniqueConstraint(
            "request_id", "position", name=op.f("uq_funding_line_items_request_id")
        ),
    )
    op.create_table(
        "request_approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"], ["users.id"], name=op.f("fk_request_approvals_approver_id")
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            name=op.f("fk_request_approvals_request_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_request_approvals")),
        sa.UniqueConstraint(
            "request_id", "round", "step", name=op.f("uq_request_approvals_request_id")
        ),
    )
    op.add_column("events", sa.Column("request_id", sa.Integer(), nullable=True))
    op.create_index(
        "idx_events_request_time",
        "events",
        ["request_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_events_request_id"), "events", "requests", ["request_id"], ["id"]
    )
    rooms = sa.table(
        "rooms",
        sa.column("name", sa.String),
        sa.column("building", sa.String),
        sa.column("capacity", sa.Integer),
    )
    # Reference data every environment needs, so it ships with the schema.
    op.bulk_insert(
        rooms,
        [
            {"name": "DV 2074", "building": "Davis Building", "capacity": 40},
            {"name": "IB 110", "building": "Instructional Building", "capacity": 120},
            {"name": "MN 1210", "building": "Maanjiwe nendamowinan", "capacity": 60},
            {
                "name": "CC 1080",
                "building": "Communication, Culture & Technology",
                "capacity": 30,
            },
            {"name": "DH 2060", "building": "Deerfield Hall", "capacity": 24},
        ],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_events_request_id"), "events", type_="foreignkey")
    op.drop_index("idx_events_request_time", table_name="events")
    op.drop_column("events", "request_id")
    op.drop_table("request_approvals")
    op.drop_table("funding_line_items")
    op.drop_index("idx_requests_club_updated", table_name="requests")
    op.drop_index("idx_requests_awaiting_updated", table_name="requests")
    op.drop_table("requests")
    op.drop_table("rooms")
    op.execute("DROP TYPE requeststatus")
    op.execute("DROP TYPE request_type_kind")
    # Postgres can't drop one enum value; finance_approver stays in userrole,
    # unused, which is harmless.
