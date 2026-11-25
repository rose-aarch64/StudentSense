from datetime import date

from pydantic import BaseModel

from modules.todos.schemas import TodoRead


class BoardDay(BaseModel):
    date: date
    today: bool
    todos: list[TodoRead]


class BoardRead(BaseModel):
    """The to-do list in its sections, in the order they are shown."""

    today: date
    overdue: list[TodoRead]
    this_week: list[BoardDay]
    next_week: list[TodoRead]
    in_two_weeks: list[TodoRead]
    future: list[TodoRead]
    undated: list[TodoRead]
    done: list[TodoRead]
    # Late by over a week, or finished over a month ago: set aside, not deleted.
    older: list[TodoRead]
