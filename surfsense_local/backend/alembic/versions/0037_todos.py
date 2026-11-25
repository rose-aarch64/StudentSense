"""Add the to-do list: tasks with a due date and a done time, in a workspace or none.

A sync's tasks carry the source and a key it finds them by; a manual task has
no key, so only a source's keys are unique.

Revision ID: 0037
Revises: 0036
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037"
down_revision: str | Sequence[str] | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("done_at", sa.DateTime(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "manual",
                "canvas",
                name="todosource",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("source_key", sa.String(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_todos_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_todos")),
        sa.UniqueConstraint("source", "source_key", name=op.f("uq_todos_source")),
    )
    op.create_index("todos_workspace", "todos", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("todos_workspace", table_name="todos")
    op.drop_table("todos")
