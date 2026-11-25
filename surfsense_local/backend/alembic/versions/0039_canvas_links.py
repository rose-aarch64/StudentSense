"""Add the Canvas links: which SurfSense item each Canvas item became.

Kinds are plain text, so a new kind of Canvas item needs no table rebuild.

Revision ID: 0039
Revises: 0038
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039"
down_revision: str | Sequence[str] | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canvas_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("canvas_id", sa.Integer(), nullable=False),
        sa.Column("local_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canvas_links")),
        sa.UniqueConstraint("kind", "canvas_id", name=op.f("uq_canvas_links_kind")),
    )


def downgrade() -> None:
    op.drop_table("canvas_links")
