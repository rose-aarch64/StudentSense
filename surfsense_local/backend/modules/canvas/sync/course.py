from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from modules.canvas import links
from modules.canvas.sync.files import Held, gone_titles, place_existing
from modules.canvas.sync.folders import ensure_folder
from modules.canvas.sync.module_folders import (
    OVERVIEW_FOLDER,
    UNSORTED_FOLDER,
    module_folder_name,
)
from modules.canvas.sync.notes import upsert_note
from modules.canvas.sync.snapshot import CourseSnapshot, FileRef, Module
from modules.canvas.sync.summaries import TITLE_PREFIX, build_summaries
from modules.canvas.sync.tasks import sync_tasks
from modules.folders.models import Folder

# Link kinds: what a Canvas id stands for.
OVERVIEW = "overview_folder"
UNSORTED = "unsorted_folder"
MODULE = "module"
PAGE = "page"


@dataclass
class PendingFile:
    """A file to fetch: new, to be kept in `folder_id`, or edited in Canvas, to
    replace the copy of the document `refresh` names."""

    ref: FileRef
    folder_id: int
    refresh: int | None = None


@dataclass
class CourseWrite:
    # Notes whose text is new or changed, for the worker to read.
    to_read: list[int] = field(default_factory=list)
    pending_files: list[PendingFile] = field(default_factory=list)
    # Kept files Canvas no longer lists: told, never deleted.
    gone: list[str] = field(default_factory=list)


def write_course(
    session: Session,
    workspace_id: int,
    course_id: int,
    snapshot: CourseSnapshot,
    *,
    fresh_workspace: bool,
) -> CourseWrite:
    """Bring one course's workspace in line with what Canvas held.

    Nothing Canvas has dropped is deleted here, and a file already held is
    filed, not fetched: the files left over are the caller's to download.
    """
    written = CourseWrite()
    sync_tasks(session, workspace_id, snapshot.assignments, revive=fresh_workspace)
    folders: dict[int, Folder] = {}

    def module_folder(module: Module) -> Folder:
        if module.id not in folders:
            name = module_folder_name(module.number, module.name)
            folders[module.id] = ensure_folder(
                session, workspace_id, MODULE, module.id, name
            )
        return folders[module.id]

    overview = ensure_folder(
        session, workspace_id, OVERVIEW, course_id, OVERVIEW_FOLDER
    )
    for summary in build_summaries(snapshot):
        _keep(
            written,
            upsert_note(
                session,
                workspace_id,
                overview.id,
                summary.kind,
                course_id,
                summary.title,
                summary.content,
            ),
        )

    used_titles: set[str] = set()
    for page in snapshot.pages:
        folder = (
            module_folder(page.module)
            if page.module is not None
            else ensure_folder(
                session, workspace_id, UNSORTED, course_id, UNSORTED_FOLDER
            )
        )
        title = f"{TITLE_PREFIX}Page · {page.title}"
        if title in used_titles:
            # Canvas allows two pages with one title; the slug keeps them apart.
            title = f"{title} ({page.slug})"
        used_titles.add(title)
        _keep(
            written,
            upsert_note(
                session,
                workspace_id,
                folder.id,
                PAGE,
                page.page_id,
                title,
                f"# {page.title}\n\n{page.body}",
            ),
        )

    for ref in snapshot.files:
        module_folder(ref.module)
    course_folder_ids = _course_folder_ids(session, snapshot, folders)
    for ref in snapshot.files:
        folder = module_folder(ref.module)
        held, document_id = place_existing(
            session, workspace_id, folder.id, ref, course_folder_ids
        )
        if held is Held.NO:
            written.pending_files.append(PendingFile(ref, folder.id))
        elif held is Held.STALE:
            written.pending_files.append(PendingFile(ref, folder.id, document_id))
    written.gone = gone_titles(
        session, workspace_id, {ref.file_id for ref in snapshot.files}
    )
    return written


def _keep(written: CourseWrite, changed: int | None) -> None:
    if changed is not None:
        written.to_read.append(changed)


def _course_folder_ids(
    session: Session, snapshot: CourseSnapshot, ensured: dict[int, Folder]
) -> set[int]:
    """Every folder of this course's modules, those used now and those left empty,
    where an earlier tool may have filed a file."""
    ids = {folder.id for folder in ensured.values()}
    for module in snapshot.modules:
        local_id = links.linked_id(session, MODULE, module.id)
        if local_id is not None:
            ids.add(local_id)
    return ids
