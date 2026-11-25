import asyncio
import time
from collections.abc import Callable
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from modules.canvas.refresh import schedule
from modules.canvas.refresh.schedule import refresh_if_enabled, refreshing_periodically
from shared.db import create_session_factory
from tests.integration.canvas.conftest import CanvasSite
from tests.integration.canvas.test_refresh_tasks import (
    assignment,
    last_pass,
    start,
    sync,
    tasks,
)

pytestmark = pytest.mark.integration

FAST = timedelta(milliseconds=50)


@pytest.fixture
def factory(engine: Engine) -> sessionmaker[Session]:
    """The session factory the schedule is handed, over the test's database."""
    return create_session_factory(engine)


async def wait_until(condition: Callable[[], bool], seconds: float = 3.0) -> None:
    """Poll until `condition` holds, failing the test if it never does."""
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "the condition never held"
        await asyncio.sleep(0.02)


async def synced_with_one_task(
    client: AsyncClient, site: CanvasSite
) -> tuple[int, dict]:
    """A synced class with one task due on 1 Dec, and its Canvas data to change."""
    data = site.course(await start(client, site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    return workspace, data


async def test_a_pass_with_the_setting_off_asks_canvas_nothing(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """The switch is the user's consent to use the token on its own."""
    await synced_with_one_task(client, canvas_site)
    mark = len(canvas_site.asked)

    assert await refresh_if_enabled(factory) is None
    assert len(canvas_site.asked) == mark


async def test_a_pass_with_no_connection_returns_none(
    factory: sessionmaker[Session],
) -> None:
    """Nothing to refresh until Canvas is connected."""
    assert await refresh_if_enabled(factory) is None


async def test_a_pass_with_the_setting_on_refreshes(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """What the loop does each time it wakes."""
    workspace, data = await synced_with_one_task(client, canvas_site)
    await client.patch("/canvas/connection", json={"auto_refresh": True})
    data.assignments = [assignment(31, "Lab 1", due="2026-12-08T05:00:00Z")]

    result = await refresh_if_enabled(factory)

    assert result is not None
    assert result.classes == 1
    assert (await tasks(client, workspace))["Lab 1"]["due_at"].startswith("2026-12-08")


async def test_a_pass_stops_asking_once_canvas_is_disconnected(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """Disconnecting takes the setting with it, so the next pass asks nothing."""
    await synced_with_one_task(client, canvas_site)
    await client.patch("/canvas/connection", json={"auto_refresh": True})
    await client.delete("/canvas/connection")
    mark = len(canvas_site.asked)

    assert await refresh_if_enabled(factory) is None
    assert len(canvas_site.asked) == mark


async def test_the_loop_runs_a_pass_and_stops_promptly(
    client: AsyncClient,
    canvas_site: CanvasSite,
    factory: sessionmaker[Session],
    engine: Engine,
) -> None:
    """A pass runs on its own, and leaving the app does not wait on the next one."""
    await synced_with_one_task(client, canvas_site)
    await client.patch("/canvas/connection", json={"auto_refresh": True})

    async with refreshing_periodically(factory, first_after=FAST, every=FAST):
        await wait_until(lambda: last_pass(engine)[0] is not None)
        stopping = time.monotonic()

    assert time.monotonic() - stopping < 2


async def test_a_failing_pass_does_not_end_the_loop(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One bad pass waits for the next; it never takes the loop down."""
    calls: list[int] = []

    async def flaky(_factory: sessionmaker[Session]) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("the first pass fails")

    monkeypatch.setattr(schedule, "refresh_if_enabled", flaky)

    async with refreshing_periodically(factory, first_after=FAST, every=FAST):
        await wait_until(lambda: len(calls) >= 2)
