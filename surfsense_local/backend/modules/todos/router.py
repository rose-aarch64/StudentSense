from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from api.dependencies import SessionDep
from modules.todos.models import Todo
from modules.todos.schemas import TodoCreate, TodoRead, TodoUpdate
from modules.workspaces.models import Workspace

router = APIRouter(prefix="/todos", tags=["todos"])


def get_todo(todo_id: int, session: SessionDep) -> Todo:
    """Resolve the task in the path, or fail the request before the handler."""
    todo = session.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")

    return todo


TodoDep = Annotated[Todo, Depends(get_todo)]


@router.get(
    "",
    response_model=list[TodoRead],
    summary="List tasks, open ones first, soonest due first",
)
def list_todos(
    session: SessionDep, workspace_id: int | None = None, done: bool | None = None
) -> Sequence[Todo]:
    query = select(Todo)

    if workspace_id is not None:
        query = query.where(Todo.workspace_id == workspace_id)
    if done is not None:
        query = query.where(
            Todo.done_at.is_not(None) if done else Todo.done_at.is_(None)
        )

    # Dated tasks before undated ones, and finished ones after every open one.
    return session.scalars(
        query.order_by(
            Todo.done_at.is_not(None), Todo.due_at.is_(None), Todo.due_at, Todo.id
        )
    ).all()


@router.post(
    "",
    response_model=TodoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a task",
)
def create_todo(payload: TodoCreate, session: SessionDep) -> Todo:
    if (
        payload.workspace_id is not None
        and session.get(Workspace, payload.workspace_id) is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "workspace not found")

    todo = Todo(
        title=payload.title, due_at=payload.due_at, workspace_id=payload.workspace_id
    )
    session.add(todo)
    # The id and the timestamps are assigned by the database, and the response
    # needs them before the dependency commits.
    session.flush()
    return todo


@router.patch(
    "/{todo_id}",
    response_model=TodoRead,
    summary="Edit a task, or check or uncheck it",
)
def update_todo(todo: TodoDep, payload: TodoUpdate, session: SessionDep) -> Todo:
    changed = payload.model_fields_set

    if "title" in changed:
        todo.title = payload.title
    if "due_at" in changed:
        todo.due_at = payload.due_at
    if "done" in changed:
        if not payload.done:
            todo.done_at = None
        elif todo.done_at is None:
            todo.done_at = datetime.now(UTC)

    session.flush()
    return todo


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_todo(todo: TodoDep, session: SessionDep) -> Response:
    session.delete(todo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
