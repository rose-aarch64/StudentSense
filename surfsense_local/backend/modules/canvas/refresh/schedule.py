"""Refreshes the to-do list from Canvas a minute after the API starts, then every six
hours, for as long as the API runs and the user has turned the refresh on."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from modules.canvas.models import CanvasConnection
from modules.canvas.refresh.run import RefreshResult, refresh_tasks

# Long enough for the app to finish starting before it reaches out.
FIRST_AFTER = timedelta(minutes=1)
# Whatever the outcome: a failed pass waits for the next one, never retried at once.
EVERY = timedelta(hours=6)
# How long stopping waits for a pass under way before cancelling it.
STOP_WITHIN = timedelta(seconds=2)

logger = logging.getLogger(__name__)


async def refresh_if_enabled(factory: sessionmaker[Session]) -> RefreshResult | None:
    """One pass, only when Canvas is connected and the user has switched it on."""
    if not await asyncio.to_thread(_enabled, factory):
        return None
    return await asyncio.to_thread(refresh_tasks, factory)


def _enabled(factory: sessionmaker[Session]) -> bool:
    with factory() as session:
        row = session.get(CanvasConnection, 1)
        return row is not None and row.auto_refresh


@asynccontextmanager
async def refreshing_periodically(
    factory: sessionmaker[Session],
    *,
    first_after: timedelta = FIRST_AFTER,
    every: timedelta = EVERY,
) -> AsyncIterator[None]:
    stopping = asyncio.Event()
    task = asyncio.create_task(
        _periodically(factory, stopping, first_after, every), name="canvas-refresh"
    )
    try:
        yield
    finally:
        stopping.set()
        # A pass under way gets a moment to finish; its database work is in sessions
        # of its own on a worker thread, which a cancel does not close.
        with suppress(TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), STOP_WITHIN.total_seconds())
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def _periodically(
    factory: sessionmaker[Session],
    stopping: asyncio.Event,
    first_after: timedelta,
    every: timedelta,
) -> None:
    wait = first_after
    # The loop ends on `stopping`, not on the cancel alone.
    while True:
        with suppress(TimeoutError):
            await asyncio.wait_for(stopping.wait(), wait.total_seconds())
        if stopping.is_set():
            return
        try:
            await refresh_if_enabled(factory)
        except Exception:
            logger.exception("could not refresh the to-do list from Canvas")
        wait = every
