import enum
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from modules.canvas import links
from modules.canvas.models import CanvasLink
from modules.canvas.sync.snapshot import FileRef
from modules.documents.models import Document, DocumentStatus, DocumentType
from modules.documents.original_file import emptied_document_dir, stored_name
from modules.documents.storage import (
    stream_upload,
    suffix_of,
    title_of,
    validate_upload,
)
from shared.config import get_storage_settings

FILE = "file"


class Held(enum.Enum):
    """Whether a Canvas file is already kept here, and if so whether it is current."""

    NO = "no"
    CURRENT = "current"
    STALE = "stale"


def place_existing(
    session: Session,
    workspace_id: int,
    folder_id: int,
    ref: FileRef,
    course_folder_ids: set[int],
) -> tuple[Held, int | None]:
    """File a file under its module if it is already held, so it is never fetched
    twice, and say whether Canvas has since edited it. Held means linked to its
    Canvas id, or an unlinked file of the same title in one of this course's
    folders, as an earlier tool left it; the latter is taken as current."""
    held = _linked(session, workspace_id, ref.file_id) or _adopted(
        session, workspace_id, ref.name, course_folder_ids
    )
    if held is None:
        return Held.NO, None
    held.folder_id = folder_id
    links.remember(session, FILE, ref.file_id, held.id)
    if _fingerprint(held) is None:
        _stamp(held, ref)
        return Held.CURRENT, held.id
    return (Held.STALE if is_stale(held, ref) else Held.CURRENT), held.id


def is_stale(document: Document, ref: FileRef) -> bool:
    """Canvas holds a different version than the one kept here."""
    kept = _fingerprint(document)
    return kept is not None and kept != (ref.size, ref.modified_at)


def store_file(
    session: Session, workspace_id: int, folder_id: int, ref: FileRef, data: bytes
) -> int | None:
    """Keep fetched bytes as a document, the way an upload is kept.

    Returns the new document's id, or None when SurfSense refuses the file or
    already holds the same bytes in this folder.
    """
    upload = UploadFile(file=BytesIO(data), filename=ref.name)
    suffix = suffix_of(upload)
    streamed = stream_upload(upload, get_storage_settings().workspace_dir(workspace_id))
    try:
        mime_type = validate_upload(streamed.path, suffix)
    except ValueError:
        streamed.path.unlink(missing_ok=True)
        return None

    twin = _twin(session, workspace_id, folder_id, streamed.digest)
    if twin is not None:
        streamed.path.unlink(missing_ok=True)
        links.remember(session, FILE, ref.file_id, twin.id)
        return None

    document = Document(
        workspace_id=workspace_id,
        title=title_of(upload),
        document_type=DocumentType.FILE,
        folder_id=folder_id,
        dedup_key=streamed.digest,
        content_hash=streamed.digest,
        document_metadata=_metadata(mime_type, streamed.size, suffix, ref),
    )
    session.add(document)
    # The file is stored under the id the database has just assigned.
    session.flush()
    destination = emptied_document_dir(workspace_id, document.id)
    streamed.path.replace(destination / stored_name(document.title, suffix))
    links.remember(session, FILE, ref.file_id, document.id)
    return document.id


def refresh_file(
    session: Session, document_id: int, ref: FileRef, data: bytes
) -> str | None:
    """Replace a document's file with the edited version, keeping the document.

    Returns its title when replaced, or None when the new bytes are refused or
    already held in the folder, so a broken re-upload never costs a good copy.
    The document is left to be read again.
    """
    document = session.get(Document, document_id)
    if document is None:
        return None
    upload = UploadFile(file=BytesIO(data), filename=ref.name)
    suffix = suffix_of(upload)
    streamed = stream_upload(
        upload, get_storage_settings().workspace_dir(document.workspace_id)
    )
    try:
        mime_type = validate_upload(streamed.path, suffix)
    except ValueError:
        streamed.path.unlink(missing_ok=True)
        return None
    twin = _twin(session, document.workspace_id, document.folder_id, streamed.digest)
    if twin is not None and twin.id != document.id:
        streamed.path.unlink(missing_ok=True)
        return None

    # Only now is the old copy cleared: the new one has passed every check.
    destination = emptied_document_dir(document.workspace_id, document.id)
    streamed.path.replace(destination / stored_name(document.title, suffix))
    document.dedup_key = streamed.digest
    document.content_hash = streamed.digest
    document.document_metadata = _metadata(mime_type, streamed.size, suffix, ref)
    document.status = DocumentStatus.PENDING
    document.error_message = None
    return document.title


def changed_titles(session: Session, refs: list[FileRef]) -> list[str]:
    """Titles of the kept files whose Canvas version has since changed."""
    changed = []
    for ref in refs:
        held = _by_canvas_id(session, ref.file_id)
        if held is not None and is_stale(held, ref):
            changed.append(held.title)
    return changed


def gone_titles(session: Session, workspace_id: int, present: set[int]) -> list[str]:
    """Titles of the files kept for this workspace that Canvas no longer lists.

    Reported and never deleted: the student may still want them.
    """
    rows = session.execute(
        select(CanvasLink.canvas_id, Document.title)
        .join(Document, Document.id == CanvasLink.local_id)
        .where(CanvasLink.kind == FILE, Document.workspace_id == workspace_id)
        .order_by(Document.id)
    )
    return [title for canvas_id, title in rows if canvas_id not in present]


def _metadata(mime_type: str, size: int, suffix: str, ref: FileRef) -> dict:
    return {
        "mime_type": mime_type,
        "size_bytes": size,
        "suffix": suffix,
        "canvas": {
            "file_id": ref.file_id,
            "size": ref.size,
            "modified_at": ref.modified_at,
        },
    }


def _fingerprint(document: Document) -> tuple[int | None, str | None] | None:
    kept = (document.document_metadata or {}).get("canvas")
    if kept is None:
        return None
    return kept.get("size"), kept.get("modified_at")


def _stamp(document: Document, ref: FileRef) -> None:
    """Record the version a file adopted from an earlier tool is taken to be."""
    # A new dict: SQLAlchemy does not see a change made inside a JSON value.
    document.document_metadata = {
        **(document.document_metadata or {}),
        "canvas": {
            "file_id": ref.file_id,
            "size": ref.size,
            "modified_at": ref.modified_at,
        },
    }


def _twin(
    session: Session, workspace_id: int, folder_id: int | None, digest: str
) -> Document | None:
    return session.scalar(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.folder_id == folder_id,
            Document.dedup_key == digest,
        )
    )


def _by_canvas_id(session: Session, file_id: int) -> Document | None:
    local_id = links.linked_id(session, FILE, file_id)
    return session.get(Document, local_id) if local_id is not None else None


def _linked(session: Session, workspace_id: int, file_id: int) -> Document | None:
    held = _by_canvas_id(session, file_id)
    if held is None or held.workspace_id != workspace_id:
        return None
    return held


def _adopted(
    session: Session, workspace_id: int, name: str, course_folder_ids: set[int]
) -> Document | None:
    taken = links.linked_ids(session, FILE)
    return session.scalars(
        select(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.document_type == DocumentType.FILE,
            Document.title == _title(name),
            Document.folder_id.in_(course_folder_ids),
            Document.id.not_in(taken),
        )
        .order_by(Document.id)
    ).first()


def _title(name: str) -> str:
    return title_of(UploadFile(file=BytesIO(b""), filename=name))
