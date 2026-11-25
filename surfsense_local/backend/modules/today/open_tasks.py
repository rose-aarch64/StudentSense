from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.today.picture import OpenTask
from modules.todos.models import Todo
from modules.workspaces.models import Workspace


def load_open_tasks(session: Session) -> list[OpenTask]:
    """Every unfinished task in every workspace, soonest due first."""
    rows = session.execute(
        select(Todo.id, Todo.title, Todo.due_at, Workspace.name)
        .join(Workspace, Workspace.id == Todo.workspace_id, isouter=True)
        .where(Todo.done_at.is_(None))
        .order_by(Todo.due_at.is_(None), Todo.due_at, Todo.id)
    )
    return [OpenTask(id, title, due_at, course) for id, title, due_at, course in rows]
