from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas import links
from modules.folders.ensure_path import ensure_folder_path
from modules.folders.models import Folder, FolderState
from modules.folders.names import name_key
from modules.source_roots.managed_root import ensure_managed_root


def ensure_folder(
    session: Session, workspace_id: int, kind: str, canvas_id: int, name: str
) -> Folder:
    """The folder of a Canvas item, at the top of the workspace's Library.

    The linked one, renamed if its name changed; else a top-level folder that
    already bears the name, so a class set up earlier is not remade; else a new one.
    """
    root = ensure_managed_root(session, workspace_id)
    folder = _linked(session, workspace_id, kind, canvas_id)
    if folder is None:
        folder = ensure_folder_path(session, root, [name])
        links.remember(session, kind, canvas_id, folder.id)
    elif folder.name != name and not _name_taken(session, folder, name):
        folder.name = name
        folder.name_key = name_key(name)
    return folder


def _linked(
    session: Session, workspace_id: int, kind: str, canvas_id: int
) -> Folder | None:
    local_id = links.linked_id(session, kind, canvas_id)
    folder = session.get(Folder, local_id) if local_id is not None else None
    if (
        folder is None
        or folder.workspace_id != workspace_id
        or folder.state is not FolderState.READY
    ):
        return None
    return folder


def _name_taken(session: Session, folder: Folder, name: str) -> bool:
    return (
        session.scalar(
            select(Folder.id).where(
                Folder.parent_id == folder.parent_id,
                Folder.name_key == name_key(name),
                Folder.state.in_((FolderState.READY, FolderState.PLACEHOLDER)),
                Folder.id != folder.id,
            )
        )
        is not None
    )
