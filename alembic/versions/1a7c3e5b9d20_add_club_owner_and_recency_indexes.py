"""add indexes for a lead's club list and the admin's newest-first list

Revision ID: 1a7c3e5b9d20
Revises: 9c2e7b1d4a6f
Create Date: 2026-11-26 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "1a7c3e5b9d20"
down_revision: str | Sequence[str] | None = "9c2e7b1d4a6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GET /clubs for a club lead: WHERE submitter_id = ? ORDER BY updated_at, id.
    op.create_index(
        "idx_clubs_submitter_updated", "clubs", ["submitter_id", "updated_at", "id"]
    )
    # GET /clubs for an admin with no status filter: ORDER BY updated_at, id.
    op.create_index("idx_clubs_updated", "clubs", ["updated_at", "id"])


def downgrade() -> None:
    op.drop_index("idx_clubs_updated", table_name="clubs")
    op.drop_index("idx_clubs_submitter_updated", table_name="clubs")
