from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

# One fixed zone, by name so daylight saving moves with it. Canvas stores due
# times in UTC, where 11:59 PM lands on the next day.
BOARD_ZONE = ZoneInfo("America/New_York")
# Further behind than this, a task is set aside from the main list, not deleted.
LATE_DAYS = 7
DONE_DAYS = 30
_SATURDAY = 5


class Dated(Protocol):
    id: int
    due_at: datetime | None
    done_at: datetime | None


@dataclass(frozen=True)
class Day[T: Dated]:
    date: date
    today: bool
    items: list[T]


@dataclass(frozen=True)
class Board[T: Dated]:
    today: date
    overdue: list[T]
    this_week: list[Day[T]]
    next_week: list[T]
    in_two_weeks: list[T]
    future: list[T]
    undated: list[T]
    done: list[T]
    # Late or finished long ago: kept, and shown only when asked for.
    older: list[T]


def local_time(moment: datetime) -> datetime:
    """A stored moment, which has no zone attached, in the board's zone."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(BOARD_ZONE)


def _by_due(item: Dated) -> tuple[datetime, int]:
    assert item.due_at is not None
    return local_time(item.due_at), item.id


def build_board[T: Dated](items: list[T], now: datetime) -> Board[T]:
    """Every task in its section, worked out from the dates and `now` alone.

    Nothing is stored: the board is rebuilt on each read, so a task moves
    sections as the days pass. Weeks run Sunday to Saturday, and this week is
    today through the coming Saturday.
    """
    local_now = now.astimezone(BOARD_ZONE)
    today = local_now.date()
    saturday = today + timedelta(days=(_SATURDAY - today.weekday()) % 7)
    days = {today + timedelta(days=n): [] for n in range((saturday - today).days + 1)}
    overdue: list[T] = []
    next_week: list[T] = []
    in_two_weeks: list[T] = []
    future: list[T] = []
    undated: list[T] = []
    done: list[T] = []
    older: list[T] = []

    # Insertion order first, so every later sort is stable on it.
    for item in sorted(items, key=lambda i: i.id):
        if item.done_at is not None:
            finished = local_time(item.done_at)
            long_ago = local_now - finished > timedelta(days=DONE_DAYS)
            (older if long_ago else done).append(item)
        elif item.due_at is None:
            undated.append(item)
        else:
            due = local_time(item.due_at).date()
            if due < today:
                late = (today - due).days
                (older if late > LATE_DAYS else overdue).append(item)
            elif due <= saturday:
                days[due].append(item)
            elif due <= saturday + timedelta(days=7):
                next_week.append(item)
            elif due <= saturday + timedelta(days=14):
                in_two_weeks.append(item)
            else:
                future.append(item)

    return Board(
        today=today,
        overdue=sorted(overdue, key=_by_due),
        this_week=[
            Day(day, day == today, sorted(found, key=_by_due))
            for day, found in days.items()
        ],
        next_week=sorted(next_week, key=_by_due),
        in_two_weeks=sorted(in_two_weeks, key=_by_due),
        future=sorted(future, key=_by_due),
        undated=undated,
        done=sorted(done, key=_most_recent, reverse=True),
        older=sorted(older, key=_most_recent, reverse=True),
    )


def _most_recent(item: Dated) -> datetime:
    """When it was finished, else when it was due."""
    moment = item.done_at or item.due_at
    assert moment is not None
    return local_time(moment)
