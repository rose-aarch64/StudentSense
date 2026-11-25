from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas import links
from modules.todos.models import Todo, TodoSource

ASSIGNMENT = "assignment"
# A submission Canvas has received counts as the work done.
HANDED_IN = {"submitted", "graded", "pending_review"}


def sync_tasks(
    session: Session, workspace_id: int, assignments: list[dict], *, revive: bool
) -> None:
    """One task per assignment, found again by the assignment's id.

    The sync owns a task's title and due date, and may mark it done when the
    work is handed in; it never clears a check. A task the user deleted stays
    deleted, unless the whole workspace was made fresh (`revive`), whose tasks
    went with it. Nothing is deleted for Canvas having dropped an assignment.
    """
    for assignment in assignments:
        todo = _task(session, assignment["id"], revive=revive)
        if todo is None:
            continue
        todo.workspace_id = workspace_id
        todo.title = assignment.get("name") or f"Assignment {assignment['id']}"
        todo.due_at = _parse(assignment.get("due_at"))
        state = (assignment.get("submission") or {}).get("workflow_state")
        if state in HANDED_IN and todo.done_at is None:
            todo.done_at = datetime.now(UTC)
        session.flush()
        links.remember(session, ASSIGNMENT, assignment["id"], todo.id)


def _task(session: Session, assignment_id: int, *, revive: bool) -> Todo | None:
    local_id = links.linked_id(session, ASSIGNMENT, assignment_id)
    todo = session.get(Todo, local_id) if local_id is not None else None
    if todo is not None:
        return todo
    if local_id is not None and not revive:
        return None  # the user deleted it
    key = f"{ASSIGNMENT}:{assignment_id}"
    todo = session.scalar(
        select(Todo).where(Todo.source == TodoSource.CANVAS, Todo.source_key == key)
    )
    if todo is None:
        todo = Todo(source=TodoSource.CANVAS, source_key=key, title="")
        session.add(todo)
    return todo


def _parse(moment: str | None) -> datetime | None:
    return datetime.fromisoformat(moment) if moment else None
