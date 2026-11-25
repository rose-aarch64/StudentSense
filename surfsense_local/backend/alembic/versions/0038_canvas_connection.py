"""Add the Canvas connection: the school's address and the encrypted token that reads it.

One row, like the web search settings. The token is encrypted with the install's
secret, as a provider's key is.

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0038"
down_revision: str | Sequence[str] | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canvas_connection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("token_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name=op.f("ck_canvas_connection_singleton")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canvas_connection")),
    )


def downgrade() -> None:
    op.drop_table("canvas_connection")
