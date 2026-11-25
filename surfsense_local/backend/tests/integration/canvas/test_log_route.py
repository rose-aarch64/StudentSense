import pytest
from httpx import AsyncClient

from modules.canvas.runlog.log import RunLog

pytestmark = pytest.mark.integration


def log_of(client: AsyncClient) -> RunLog:
    """The app's own log, which a test fills as a run would."""
    return client._transport.app.state.canvas_log  # type: ignore[attr-defined]


async def test_the_log_is_idle_before_any_run(client: AsyncClient) -> None:
    """A fresh install, or a restarted API, has nothing to show."""
    shown = await client.get("/canvas/log")

    assert shown.status_code == 200
    assert shown.json() == {
        "run": 0,
        "kind": None,
        "state": "idle",
        "entries": [],
        "next": 0,
    }


async def test_it_returns_the_entries_after_a_number(client: AsyncClient) -> None:
    """The panel asks only for lines it has not seen."""
    handle = log_of(client).start("sync")
    handle.add("sync_started")
    handle.add("class_started", name="Bio")
    handle.add("file_failed", "error", name="Week1.pdf")

    shown = (await client.get("/canvas/log", params={"run": 1, "after": 1})).json()

    assert shown["state"] == "running"
    assert shown["next"] == 3
    assert [e["n"] for e in shown["entries"]] == [2, 3]
    assert shown["entries"][0] == {
        "n": 2,
        "level": "info",
        "code": "class_started",
        "params": {"name": "Bio"},
    }
    assert shown["entries"][1]["level"] == "error"


async def test_another_run_id_returns_the_whole_log(client: AsyncClient) -> None:
    """A page that outlived a run starts over from the current one."""
    handle = log_of(client).start("sync")
    for code in ("a", "b", "c"):
        handle.add(code)

    shown = (await client.get("/canvas/log", params={"run": 99, "after": 2})).json()

    assert [e["code"] for e in shown["entries"]] == ["a", "b", "c"]


async def test_a_negative_after_is_rejected(client: AsyncClient) -> None:
    """A line number is never below zero."""
    refused = await client.get("/canvas/log", params={"after": -1})

    assert refused.status_code == 422
