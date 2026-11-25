from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas import links
from modules.source_roots.managed_root import ensure_managed_root
from modules.workspaces.models import Workspace


def ensure_workspace(
    session: Session, course_id: int, name: str
) -> tuple[Workspace, bool]:
    """The workspace of a course, and whether it was made just now.

    The linked one, else one already named for it, else a new one. A link to a
    workspace the user deleted is made good again.
    """
    workspace = _linked(session, course_id) or _adopted(session, name)
    created = workspace is None
    if workspace is None:
        workspace = Workspace(name=name)
        session.add(workspace)
        session.flush()
        ensure_managed_root(session, workspace.id)
    workspace.name = name
    links.remember(session, links.COURSE, course_id, workspace.id)
    return workspace, created


def _linked(session: Session, course_id: int) -> Workspace | None:
    local_id = links.linked_id(session, links.COURSE, course_id)
    return session.get(Workspace, local_id) if local_id is not None else None


def _adopted(session: Session, name: str) -> Workspace | None:
    """A workspace set up by hand or by an earlier tool, named exactly for the
    course and not yet another course's."""
    taken = links.linked_ids(session, links.COURSE)
    return session.scalars(
        select(Workspace)
        .where(Workspace.name == name, Workspace.id.not_in(taken))
        .order_by(Workspace.id)
    ).first()
