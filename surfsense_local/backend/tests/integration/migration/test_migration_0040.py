"""Revision 0040: workspace folders, and an icon and a folder on each workspace."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, text

from alembic import command
from shared.db import create_db_engine

pytestmark = pytest.mark.integration


def _config(engine: Engine) -> Config:
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parents[3] / "alembic")
    )
    config.attributes["engine"] = engine
    return config


def _upgraded(tmp_path: Path) -> Engine:
    engine = create_db_engine(tmp_path / "t.db")
    command.upgrade(_config(engine), "0040")
    return engine


def test_upgrading_keeps_the_chats_and_documents_of_existing_workspaces(
    tmp_path: Path,
) -> None:
    """Rebuilding `workspaces` would cascade-delete every chat and document in it."""
    engine = create_db_engine(tmp_path / "t.db")
    command.upgrade(_config(engine), "0039")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO workspaces(id, name) VALUES (1, 'Bio')"))
        connection.execute(
            text(
                "INSERT INTO chat_threads(id, workspace_id, title, created_at) "
                "VALUES (1, 1, 'Notes', '2026-06-02 14:00:00')"
            )
        )

    command.upgrade(_config(engine), "0040")

    with engine.begin() as connection:
        threads = connection.execute(text("SELECT COUNT(*) FROM chat_threads")).scalar()
    assert threads == 1


def test_the_folder_table_and_workspace_columns_exist_after_upgrading(
    tmp_path: Path,
) -> None:
    """A workspace can name a folder and carry an icon key."""
    engine = _upgraded(tmp_path)

    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO workspace_folders(name) VALUES ('2026/FA')")
        )
        connection.execute(
            text(
                "INSERT INTO workspaces(name, folder_id, icon) "
                "VALUES ('Bio', 1, 'camera')"
            )
        )
        row = connection.execute(
            text("SELECT folder_id, icon FROM workspaces WHERE name = 'Bio'")
        ).one()

    assert tuple(row) == (1, "camera")


def test_deleting_a_folder_unfiles_its_workspaces(tmp_path: Path) -> None:
    """Folders group workspaces; removing one never removes a workspace."""
    engine = _upgraded(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO workspace_folders(name) VALUES ('2026/FA')")
        )
        connection.execute(
            text("INSERT INTO workspaces(name, folder_id) VALUES ('Bio', 1)")
        )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM workspace_folders WHERE id = 1"))
        row = connection.execute(
            text("SELECT folder_id FROM workspaces WHERE name = 'Bio'")
        ).one()

    assert row[0] is None


def test_downgrading_removes_both_additions(tmp_path: Path) -> None:
    """Going back leaves the workspaces table as it was."""
    engine = _upgraded(tmp_path)

    command.downgrade(_config(engine), "0039")

    with engine.begin() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(workspaces)"))
        }
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }
    assert "icon" not in columns and "folder_id" not in columns
    assert "workspace_folders" not in tables


def test_downgrading_keeps_the_chats_and_documents_of_filed_workspaces(
    tmp_path: Path,
) -> None:
    """A rebuild of `workspaces` would cascade-delete every chat in it."""
    engine = _upgraded(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO workspace_folders(name) VALUES ('2026/FA')")
        )
        connection.execute(
            text("INSERT INTO workspaces(id, name, folder_id) VALUES (1, 'Bio', 1)")
        )
        connection.execute(
            text(
                "INSERT INTO chat_threads(id, workspace_id, title, created_at) "
                "VALUES (1, 1, 'Notes', '2026-06-02 14:00:00')"
            )
        )

    command.downgrade(_config(engine), "0039")

    with engine.begin() as connection:
        threads = connection.execute(text("SELECT COUNT(*) FROM chat_threads")).scalar()
        workspaces = connection.execute(
            text("SELECT COUNT(*) FROM workspaces")
        ).scalar()
    assert (threads, workspaces) == (1, 1)
