"""Add the Canvas to-do refresh setting and its last result to the connection.

`auto_refresh` is off until the user turns it on, because the refresh uses the
saved token with nobody there. `refreshed_at` and `refresh_error` record how
the last pass went, for Settings to show.

Columns are added and dropped in place, never in batch mode: a batch rebuild
drops the table, and with foreign keys on that cascades into dependent rows.

Revision ID: 0041
Revises: 0040
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0041"
down_revision: str | Sequence[str] | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE canvas_connection "
        "ADD COLUMN auto_refresh BOOLEAN NOT NULL DEFAULT 0"
    )
    op.execute("ALTER TABLE canvas_connection ADD COLUMN refreshed_at DATETIME")
    op.execute("ALTER TABLE canvas_connection ADD COLUMN refresh_error VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE canvas_connection DROP COLUMN refresh_error")
    op.execute("ALTER TABLE canvas_connection DROP COLUMN refreshed_at")
    op.execute("ALTER TABLE canvas_connection DROP COLUMN auto_refresh")
