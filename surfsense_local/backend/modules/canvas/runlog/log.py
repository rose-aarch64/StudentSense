"""The last Canvas run's log, in memory: what Sync and Check read, keep and fail on.

Never written to disk, and holds names and counts only: no token, no link.
"""

import threading
from collections import deque
from dataclasses import dataclass

# A very long sync drops its oldest lines rather than grow without bound.
MAX_ENTRIES = 1000

Param = str | int | float | bool


@dataclass(frozen=True)
class Entry:
    n: int
    level: str
    code: str
    params: dict[str, Param]


@dataclass(frozen=True)
class LogRead:
    run: int
    kind: str | None
    state: str
    entries: list[Entry]
    next: int


class RunLog:
    """One run at a time: starting another replaces the log."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._run = 0
        self._kind: str | None = None
        self._state = "idle"
        self._entries: deque[Entry] = deque(maxlen=MAX_ENTRIES)
        self._last = 0

    def start(self, kind: str) -> "RunHandle":
        with self._lock:
            self._run += 1
            self._kind = kind
            self._state = "running"
            self._entries.clear()
            self._last = 0
            return RunHandle(self, self._run)

    def read(self, run: int | None, after: int) -> LogRead:
        """The entries after `after` of run `run`, or the whole current log when
        `run` is not the current run, which a page that outlived a run asks about."""
        with self._lock:
            entries = list(self._entries)
            if run == self._run:
                entries = [e for e in entries if e.n > after]
            return LogRead(
                run=self._run,
                kind=self._kind,
                state=self._state,
                entries=entries,
                next=entries[-1].n if entries else (after if run == self._run else 0),
            )

    def _append(
        self, run: int, level: str, code: str, params: dict[str, Param]
    ) -> bool:
        with self._lock:
            if run != self._run or self._state != "running":
                return False
            self._last += 1
            self._entries.append(Entry(self._last, level, code, params))
            return True

    def _finish(self, run: int, state: str) -> None:
        with self._lock:
            if run == self._run and self._state == "running":
                self._state = state


class RunHandle:
    """What a run writes through. A handle of an older run writes nothing."""

    def __init__(self, log: RunLog, run: int) -> None:
        self._log = log
        self._run = run
        self.errors = 0

    def add(self, code: str, level: str = "info", **params: object) -> None:
        # Writing a line must never break the sync that writes it.
        try:
            plain = {
                key: value if isinstance(value, Param) else str(value)
                for key, value in params.items()
            }
            if self._log._append(self._run, level, code, plain) and level == "error":
                self.errors += 1
        except Exception:
            return

    def finish(self, state: str) -> None:
        self._log._finish(self._run, state)


class _NullHandle(RunHandle):
    """For a run nobody is watching: every write is dropped."""

    def __init__(self) -> None:
        self.errors = 0

    def add(self, code: str, level: str = "info", **params: object) -> None:
        return

    def finish(self, state: str) -> None:
        return


NULL_HANDLE: RunHandle = _NullHandle()
