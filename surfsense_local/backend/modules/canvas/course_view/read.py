from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas import links
from modules.canvas.course_view.schemas import CourseView, ItemView, ModuleView
from modules.canvas.models import CanvasLink
from modules.canvas.sync.assignment_notes import ASSIGNMENT_NOTE
from modules.canvas.sync.course import MODULE, PAGE
from modules.canvas.sync.files import FILE
from modules.canvas.sync.outline import OUTLINE_KEY
from modules.canvas.sync.summaries import MODULES_NOTE
from modules.canvas.sync.textbook_folder import TEXTBOOK
from modules.documents.models import Document
from modules.folders.models import Folder, FolderState

# The summary notes a view offers by name, and the link kind each one has.
_NOTE_KINDS = {
    "syllabus": "syllabus_note",
    "announcements": "announcements_note",
    "assignments": "assignments_note",
    "links": "links_note",
}
# Outline item type -> the link kind its Canvas id is found under.
_ITEM_KINDS = {
    "Page": PAGE,
    "File": FILE,
    "Assignment": ASSIGNMENT_NOTE,
    "Quiz": ASSIGNMENT_NOTE,
    "Discussion": ASSIGNMENT_NOTE,
}

NOT_SYNCED = CourseView(synced=False)


def read_course_view(session: Session, workspace_id: int) -> CourseView:
    """A class's modules in Canvas's order, each item tied to the row it became."""
    course_id = session.scalar(
        select(CanvasLink.canvas_id).where(
            CanvasLink.kind == links.COURSE, CanvasLink.local_id == workspace_id
        )
    )
    if course_id is None:
        return NOT_SYNCED
    outline = _outline(session, workspace_id, course_id)
    if outline is None:
        return CourseView(synced=False, needs_sync=True)

    local = _local_ids(session, outline)
    document_ids = _own_documents(session, workspace_id, local)
    folder_ids = _own_folders(session, workspace_id, local)
    return CourseView(
        synced=True,
        textbook_folder_id=_one_folder(
            session, workspace_id, links.linked_id(session, TEXTBOOK, course_id)
        ),
        notes=_notes(session, workspace_id, course_id),
        files=_files(session, workspace_id),
        modules=[
            ModuleView(
                id=module["id"],
                name=module["name"],
                folder_id=_found(local, folder_ids, MODULE, module["id"]),
                items=[_item(i, local, document_ids) for i in module["items"]],
            )
            for module in outline
        ],
    )


def _files(session: Session, workspace_id: int) -> dict[int, int]:
    """Every Canvas file this workspace holds, module files and linked files alike."""
    rows = session.execute(
        select(CanvasLink.canvas_id, Document.id)
        .join(Document, Document.id == CanvasLink.local_id)
        .where(CanvasLink.kind == FILE, Document.workspace_id == workspace_id)
    )
    return dict(rows.all())


def _outline(session: Session, workspace_id: int, course_id: int) -> list[dict] | None:
    note_id = links.linked_id(session, MODULES_NOTE, course_id)
    note = session.get(Document, note_id) if note_id is not None else None
    if note is None or note.workspace_id != workspace_id:
        return None
    return (note.document_metadata or {}).get(OUTLINE_KEY)


def _local_ids(session: Session, outline: list[dict]) -> dict[tuple[str, int], int]:
    """(link kind, Canvas id) -> local id, for everything the outline names."""
    wanted: dict[str, set[int]] = {MODULE: set(), PAGE: set(), FILE: set()}
    wanted[ASSIGNMENT_NOTE] = set()
    for module in outline:
        wanted[MODULE].add(module["id"])
        for item in module["items"]:
            kind = _ITEM_KINDS.get(item["type"])
            if kind is not None and item["canvas_id"] is not None:
                wanted[kind].add(item["canvas_id"])
    found: dict[tuple[str, int], int] = {}
    for kind, canvas_ids in wanted.items():
        if not canvas_ids:
            continue
        for link in session.scalars(
            select(CanvasLink).where(
                CanvasLink.kind == kind, CanvasLink.canvas_id.in_(canvas_ids)
            )
        ):
            found[(kind, link.canvas_id)] = link.local_id
    return found


def _own_documents(
    session: Session, workspace_id: int, local: dict[tuple[str, int], int]
) -> set[int]:
    ids = [i for (kind, _), i in local.items() if kind != MODULE]
    return set(
        session.scalars(
            select(Document.id).where(
                Document.id.in_(ids), Document.workspace_id == workspace_id
            )
        )
    )


def _own_folders(
    session: Session, workspace_id: int, local: dict[tuple[str, int], int]
) -> set[int]:
    ids = [i for (kind, _), i in local.items() if kind == MODULE]
    return set(
        session.scalars(
            select(Folder.id).where(
                Folder.id.in_(ids),
                Folder.workspace_id == workspace_id,
                Folder.state == FolderState.READY,
            )
        )
    )


def _found(
    local: dict[tuple[str, int], int], own: set[int], kind: str, canvas_id: int | None
) -> int | None:
    local_id = local.get((kind, canvas_id)) if canvas_id is not None else None
    return local_id if local_id in own else None


def _item(item: dict, local: dict, document_ids: set[int]) -> ItemView:
    kind = _ITEM_KINDS.get(item["type"])
    return ItemView(
        type=item["type"],
        title=item["title"] or "",
        document_id=(
            _found(local, document_ids, kind, item["canvas_id"]) if kind else None
        ),
        url=item["url"],
        due_at=item["due_at"],
        points=item["points"],
    )


def _notes(session: Session, workspace_id: int, course_id: int) -> dict[str, int]:
    found: dict[str, int] = {}
    for name, kind in _NOTE_KINDS.items():
        note_id = links.linked_id(session, kind, course_id)
        note = session.get(Document, note_id) if note_id is not None else None
        if note is not None and note.workspace_id == workspace_id:
            found[name] = note.id
    return found


def _one_folder(
    session: Session, workspace_id: int, folder_id: int | None
) -> int | None:
    folder = session.get(Folder, folder_id) if folder_id is not None else None
    if (
        folder is None
        or folder.workspace_id != workspace_id
        or folder.state is not FolderState.READY
    ):
        return None
    return folder.id
