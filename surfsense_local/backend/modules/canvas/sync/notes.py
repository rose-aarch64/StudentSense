from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas import links
from modules.documents.models import Document, DocumentStatus, DocumentType


def upsert_note(
    session: Session,
    workspace_id: int,
    folder_id: int,
    kind: str,
    canvas_id: int,
    title: str,
    content: str,
    metadata: dict | None = None,
) -> int | None:
    """The note of a Canvas item: the linked one, else an unlinked note with the
    same title, else a new one. Returns its id when its text must be read again.

    `metadata` is merged into the note's own; changing it alone asks for no re-read."""
    note = _linked(session, workspace_id, kind, canvas_id) or _adopted(
        session, workspace_id, kind, title
    )
    if note is None:
        note = Document(
            workspace_id=workspace_id,
            title=title,
            document_type=DocumentType.NOTE,
            content=content,
            document_metadata=metadata,
            folder_id=folder_id,
        )
        session.add(note)
        session.flush()
        links.remember(session, kind, canvas_id, note.id)
        return note.id

    links.remember(session, kind, canvas_id, note.id)
    note.title = title
    note.folder_id = folder_id
    if metadata is not None:
        _merge_metadata(note, metadata)
    if note.content == content:
        return None
    note.content = content
    # The indexed copy is stale until the worker has read the note again.
    note.status = DocumentStatus.PENDING
    return note.id


def update_note_metadata(
    session: Session, workspace_id: int, kind: str, canvas_id: int, metadata: dict
) -> None:
    """Merge `metadata` into a Canvas item's note, if it has one, leaving its text."""
    note = _linked(session, workspace_id, kind, canvas_id)
    if note is not None:
        _merge_metadata(note, metadata)


def _merge_metadata(note: Document, metadata: dict) -> None:
    # A new dict: SQLAlchemy does not see a JSON value changed in place.
    note.document_metadata = {**(note.document_metadata or {}), **metadata}


def _linked(
    session: Session, workspace_id: int, kind: str, canvas_id: int
) -> Document | None:
    local_id = links.linked_id(session, kind, canvas_id)
    note = session.get(Document, local_id) if local_id is not None else None
    if note is None or note.workspace_id != workspace_id:
        return None
    return note


def _adopted(
    session: Session, workspace_id: int, kind: str, title: str
) -> Document | None:
    taken = links.linked_ids(session, kind)
    return session.scalars(
        select(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.document_type == DocumentType.NOTE,
            Document.title == title,
            Document.id.not_in(taken),
        )
        .order_by(Document.id)
    ).first()
