"""Revision 0041: the Canvas refresh setting and its last result."""

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


def _connected_at_0040(tmp_path: Path) -> Engine:
    engine = create_db_engine(tmp_path / "t.db")
    command.upgrade(_config(engine), "0040")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO canvas_connection(id, base_url, token_ciphertext) "
                "VALUES (1, 'https://school.example', x'00')"
            )
        )
    return engine


def _connection_count(engine: Engine) -> int:
    with engine.begin() as connection:
        return connection.execute(
            text("SELECT COUNT(*) FROM canvas_connection")
        ).scalar_one()


def test_upgrading_keeps_the_connection_and_adds_the_setting_off(
    tmp_path: Path,
) -> None:
    """The refresh uses the token on its own, so it starts off."""
    engine = _connected_at_0040(tmp_path)

    command.upgrade(_config(engine), "0041")

    with engine.begin() as connection:
        row = connection.execute(
            text(
                "SELECT auto_refresh, refreshed_at, refresh_error "
                "FROM canvas_connection"
            )
        ).one()
    assert tuple(row) == (0, None, None)
    assert _connection_count(engine) == 1


def test_downgrading_drops_the_three_columns_and_keeps_the_row(
    tmp_path: Path,
) -> None:
    """In place, so the saved token survives going back."""
    engine = _connected_at_0040(tmp_path)
    command.upgrade(_config(engine), "0041")

    command.downgrade(_config(engine), "0040")

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(canvas_connection)"))
        }
    assert columns.isdisjoint({"auto_refresh", "refreshed_at", "refresh_error"})
    assert _connection_count(engine) == 1
