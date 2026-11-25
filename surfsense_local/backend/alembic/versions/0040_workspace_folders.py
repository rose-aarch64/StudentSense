"""Add workspace folders, and an icon and a folder on each workspace.

A folder only groups: deleting one sets its workspaces' folder to null, so no
workspace is lost. An icon is a short key the interface maps to a picture.

Revision ID: 0040
Revises: 0039
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0040"
down_revision: str | Sequence[str] | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspace_folders")),
    )
    # Column adds in place, not a batch: batch mode would rebuild `workspaces`,
    # and dropping the old table with foreign keys on cascades into every chat
    # and document in it. SQLite takes a named REFERENCES column that defaults
    # to NULL, which op.add_column cannot spell.
    op.add_column("workspaces", sa.Column("icon", sa.String(), nullable=True))
    op.execute(
        "ALTER TABLE workspaces ADD COLUMN folder_id INTEGER "
        "CONSTRAINT fk_workspaces_folder_id_workspace_folders "
        "REFERENCES workspace_folders (id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # In place, as the upgrade is: SQLite drops a column whose REFERENCES clause is
    # inline, and a batch rebuild would cascade into every chat and document.
    op.execute("ALTER TABLE workspaces DROP COLUMN folder_id")
    op.execute("ALTER TABLE workspaces DROP COLUMN icon")
    op.drop_table("workspace_folders")
