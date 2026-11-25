from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from api.dependencies import SessionDep
from modules.todos.board.layout import build_board
from modules.todos.board.schemas import BoardDay, BoardRead
from modules.todos.models import Todo
from modules.todos.schemas import TodoRead

router = APIRouter(prefix="/todos/board", tags=["todos"])


def _read(todos: list[Todo]) -> list[TodoRead]:
    return [TodoRead.model_validate(todo) for todo in todos]


@router.get("", response_model=BoardRead, summary="The list in its sections")
def read_board(session: SessionDep) -> BoardRead:
    board = build_board(list(session.scalars(select(Todo))), datetime.now(UTC))
    return BoardRead(
        today=board.today,
        overdue=_read(board.overdue),
        this_week=[
            BoardDay(date=day.date, today=day.today, todos=_read(day.items))
            for day in board.this_week
        ],
        next_week=_read(board.next_week),
        in_two_weeks=_read(board.in_two_weeks),
        future=_read(board.future),
        undated=_read(board.undated),
        done=_read(board.done),
        older=_read(board.older),
    )
