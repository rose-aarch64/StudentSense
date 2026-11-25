from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from modules.todos.board.layout import build_board

EASTERN = ZoneInfo("America/New_York")
# Tuesday 24 Nov 2026, 9:30 in the morning in Eastern.
NOW = datetime(2026, 11, 24, 9, 30, tzinfo=EASTERN)


@dataclass(frozen=True)
class Item:
    id: int
    due_at: datetime | None = None
    done_at: datetime | None = None


def eastern(month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    """A moment as Canvas stores it: UTC, with no zone attached."""
    local = datetime(2026, month, day, hour, minute, tzinfo=EASTERN)
    return local.astimezone(UTC).replace(tzinfo=None)


def ids(items: list[Item]) -> list[int]:
    """The ids of a section, in the order shown."""
    return [item.id for item in items]


def test_a_task_lands_in_the_section_its_due_date_names() -> None:
    """Sunday to Saturday weeks: this Saturday is Nov 28, then two more weeks."""
    board = build_board(
        [
            Item(1, eastern(11, 20)),
            Item(2, eastern(11, 26)),
            Item(3, eastern(11, 30)),
            Item(4, eastern(12, 9)),
            Item(5, eastern(12, 20)),
            Item(6, None),
        ],
        NOW,
    )

    assert ids(board.overdue) == [1]
    assert [ids(day.items) for day in board.this_week] == [[], [], [2], [], []]
    assert ids(board.next_week) == [3]
    assert ids(board.in_two_weeks) == [4]
    assert ids(board.future) == [5]
    assert ids(board.undated) == [6]


def test_this_week_has_a_header_for_every_day_left_and_marks_today() -> None:
    """Empty days still show, so the week reads as a calendar."""
    board = build_board([], NOW)

    assert [day.date for day in board.this_week] == [
        date(2026, 11, d) for d in (24, 25, 26, 27, 28)
    ]
    assert [day.today for day in board.this_week] == [True, False, False, False, False]


def test_on_a_sunday_this_week_is_the_whole_week() -> None:
    """The week starts on Sunday, so a Sunday has seven days left."""
    sunday = datetime(2026, 11, 29, 8, 0, tzinfo=EASTERN)

    board = build_board([], sunday)

    assert len(board.this_week) == 7
    assert board.this_week[-1].date == date(2026, 12, 5)


def test_on_a_saturday_this_week_is_one_day() -> None:
    """Today through the coming Saturday, and today is the Saturday."""
    saturday = datetime(2026, 11, 28, 8, 0, tzinfo=EASTERN)

    board = build_board([Item(1, eastern(11, 29))], saturday)

    assert [day.date for day in board.this_week] == [date(2026, 11, 28)]
    assert ids(board.next_week) == [1]


def test_eleven_fifty_nine_tonight_is_still_today() -> None:
    """In UTC that is already tomorrow; the day is the user's, not the server's."""
    board = build_board([Item(1, eastern(11, 24, 23, 59))], NOW)

    assert ids(board.this_week[0].items) == [1]
    assert board.overdue == []


def test_a_task_a_week_late_stays_overdue_and_older_than_that_is_set_aside() -> None:
    """Set aside is not deleted: it comes back as `older`, for a Show older button."""
    board = build_board([Item(1, eastern(11, 17)), Item(2, eastern(11, 16))], NOW)

    assert ids(board.overdue) == [1]
    assert ids(board.older) == [2]


def test_done_is_newest_first_and_a_month_old_one_is_set_aside() -> None:
    """Finished work leaves the main list after thirty days, never the database."""
    board = build_board(
        [
            Item(1, done_at=eastern(11, 20)),
            Item(2, done_at=eastern(11, 23)),
            Item(3, done_at=eastern(10, 1)),
        ],
        NOW,
    )

    assert ids(board.done) == [2, 1]
    assert ids(board.older) == [3]


def test_priority_free_ordering_is_stable_inside_a_day_and_a_section() -> None:
    """Same-day tasks keep the order they were added in; later days sort by date."""
    board = build_board(
        [
            Item(1, eastern(12, 9)),
            Item(2, eastern(12, 7)),
            Item(3, eastern(12, 7)),
            Item(4, None),
            Item(5, None),
        ],
        NOW,
    )

    assert ids(board.in_two_weeks) == [2, 3, 1]
    assert ids(board.undated) == [4, 5]


def test_overdue_runs_oldest_first() -> None:
    """The longest-waiting thing is on top."""
    board = build_board([Item(1, eastern(11, 23)), Item(2, eastern(11, 19))], NOW)

    assert ids(board.overdue) == [2, 1]
