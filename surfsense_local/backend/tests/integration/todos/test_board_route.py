from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from modules.todos.board.layout import BOARD_ZONE

pytestmark = pytest.mark.integration


def at(days_from_today: int, hour: int = 12) -> str:
    """A due time on the board's calendar, as the API takes it."""
    local = datetime.now(BOARD_ZONE).replace(
        hour=hour, minute=0, second=0, microsecond=0
    ) + timedelta(days=days_from_today)
    return local.astimezone(UTC).isoformat()


def titles(todos: list[dict]) -> list[str]:
    """The titles of a section, in the order shown."""
    return [todo["title"] for todo in todos]


async def test_the_board_sorts_tasks_into_sections_from_their_dates(
    client: AsyncClient,
) -> None:
    """The list is derived on each read; nothing about order is stored."""
    await client.post("/todos", json={"title": "late", "due_at": at(-3)})
    await client.post("/todos", json={"title": "someday"})
    await client.post("/todos", json={"title": "far", "due_at": at(60)})
    done = await client.post("/todos", json={"title": "finished"})
    await client.patch(f"/todos/{done.json()['id']}", json={"done": True})

    board = (await client.get("/todos/board")).json()

    assert titles(board["overdue"]) == ["late"]
    assert titles(board["undated"]) == ["someday"]
    assert titles(board["future"]) == ["far"]
    assert titles(board["done"]) == ["finished"]
    assert board["older"] == []
    # Today through Saturday: between one day and seven.
    assert 1 <= len(board["this_week"]) <= 7
    assert board["this_week"][0]["today"] is True
    assert board["this_week"][0]["date"] == board["today"]


async def test_a_task_long_overdue_is_set_aside_not_deleted(
    client: AsyncClient,
) -> None:
    """Aged out of the main list, and still there for a Show older button."""
    await client.post("/todos", json={"title": "orientation", "due_at": at(-800)})

    board = (await client.get("/todos/board")).json()

    assert titles(board["older"]) == ["orientation"]
    assert titles((await client.get("/todos")).json()) == ["orientation"]
