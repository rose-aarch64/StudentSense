from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas import links
from modules.workspaces.models import WorkspaceFolder


def ensure_term_folder(session: Session, term: dict | None) -> WorkspaceFolder | None:
    """The folder a term's courses are filed in, made when it is missing.

    The one linked to the term's Canvas id, else an unlinked folder with the
    term's exact name, else a new one; its name follows the term's. A course
    with no term, or in one with no dates such as "Default Term", gets none: an
    undated term is not a term worth a folder.
    """
    if (
        not term
        or not term.get("name")
        or not (term.get("start_at") or term.get("end_at"))
    ):
        return None
    name, term_id = term["name"], term.get("id")
    folder = _linked(session, term_id) if term_id is not None else None
    folder = folder or _adopted(session, name)
    if folder is None:
        folder = WorkspaceFolder(name=name)
        session.add(folder)
        session.flush()
    folder.name = name
    if term_id is not None:
        links.remember(session, links.TERM, term_id, folder.id)
    return folder


def _linked(session: Session, term_id: int) -> WorkspaceFolder | None:
    local_id = links.linked_id(session, links.TERM, term_id)
    return session.get(WorkspaceFolder, local_id) if local_id is not None else None


def _adopted(session: Session, name: str) -> WorkspaceFolder | None:
    """A folder made by hand with the term's exact name, not yet another term's."""
    taken = links.linked_ids(session, links.TERM)
    return session.scalars(
        select(WorkspaceFolder)
        .where(WorkspaceFolder.name == name, WorkspaceFolder.id.not_in(taken))
        .order_by(WorkspaceFolder.id)
    ).first()
