from dataclasses import dataclass
from datetime import datetime

from modules.todos.board.layout import BOARD_ZONE, build_board, local_time


@dataclass(frozen=True)
class OpenTask:
    id: int
    title: str
    # As stored: UTC with no zone attached.
    due_at: datetime | None
    course: str | None
    # Only unfinished tasks are loaded.
    done_at: datetime | None = None


def _line(task: OpenTask) -> str:
    where = f"[{task.course}] " if task.course else ""
    if task.due_at is None:
        return f"- {where}{task.title}"
    due = local_time(task.due_at)
    return f"- {where}{task.title}, due {due:%a %b %-d, %-I:%M %p}"


def day_picture(tasks: list[OpenTask], now: datetime) -> str:
    """The user's day as plain text, in the same sections the to-do list shows.

    Far-off, long-late and finished tasks are left out: not today's business.
    Times are Eastern, the board's zone.
    """
    board = build_board(tasks, now)
    local = now.astimezone(BOARD_ZONE)
    today, *rest_of_week = board.this_week
    sections = [
        ("Overdue:", board.overdue),
        ("Due today:", today.items),
        ("Later this week:", [t for day in rest_of_week for t in day.items]),
        ("Next week:", board.next_week),
        ("In two weeks:", board.in_two_weeks),
        ("No due date:", board.undated),
    ]
    parts = [f"It is {local:%A, %B %-d, %Y}, {local:%-I:%M %p} Eastern."]
    for heading, found in sections:
        if found:
            parts.append(heading + "\n" + "\n".join(_line(t) for t in found))
    if len(parts) == 1:
        parts.append("No open tasks.")
    return "\n\n".join(parts)
