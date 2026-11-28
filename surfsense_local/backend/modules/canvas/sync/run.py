from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session, sessionmaker

from modules.canvas.client import CanvasClient
from modules.canvas.consent import require_hosts
from modules.canvas.download import download
from modules.canvas.runlog.log import NULL_HANDLE, RunHandle
from modules.canvas.sync.connection import NotConnectedError, read_connection
from modules.canvas.sync.course import PendingFile, write_course
from modules.canvas.sync.files import refresh_file, store_file
from modules.canvas.sync.snapshot import read_course
from modules.canvas.sync.term import courses_to_sync
from modules.canvas.sync.term_folders import ensure_term_folder
from modules.canvas.sync.workspaces import ensure_workspace
from modules.documents.tasks import ingest_document
from modules.embedding.active import require_active_index

__all__ = ["CourseResult", "NotConnectedError", "run_sync"]


@dataclass
class CourseResult:
    canvas_id: int
    name: str
    workspace_id: int
    # Files edited in Canvas whose kept copy was replaced.
    refreshed: list[str] = field(default_factory=list)
    # Kept files Canvas no longer lists.
    gone: list[str] = field(default_factory=list)


def run_sync(
    factory: sessionmaker[Session],
    term: str | None = None,
    log: RunHandle = NULL_HANDLE,
) -> list[CourseResult]:
    """Read the student's Canvas and bring SurfSense in line with it.

    Canvas is read, and files fetched, with no database session open: a long
    read must not hold SQLite's write lock, which every other request in the app
    waits on. Each course is written in one short transaction, and each file
    kept in one of its own. What is read and kept is written to `log`.
    """
    log.add("sync_started")
    with factory() as session:
        # In a session of its own, closed at once: a dependency would hold the
        # request's session open through the sync and block its own writes.
        require_active_index(session)
    base_url, token = read_connection(factory)

    results: list[CourseResult] = []
    with CanvasClient(base_url, token) as canvas:
        courses = canvas.get_all(
            "/courses", {"enrollment_state": "active", "include[]": "term"}
        )
        for course in courses_to_sync(courses, term, datetime.now(UTC)):
            name = _name_of(course)
            log.add("class_started", name=name)
            snapshot = read_course(canvas, course["id"])
            log.add(
                "class_read",
                name=name,
                assignments=len(snapshot.assignments),
                announcements=len(snapshot.announcements),
                modules=len(snapshot.modules),
                pages=len(snapshot.pages),
                files=len(snapshot.files),
            )
            if snapshot.pages_tab_off:
                log.add("pages_tab_off", name=name)
            for skipped in snapshot.skipped_files:
                # A linked file that cannot be stored stays a link to Canvas.
                log.add("file_skipped", name=skipped)
            with factory() as session:
                # Before anything is written or fetched, so one prompt asks
                # for every host the course's files sit on.
                require_hosts(session, [f.url for f in snapshot.files])

            with factory() as session:
                workspace, fresh = ensure_workspace(session, course["id"], name)
                # The term's folder keeps its name; only a workspace with no
                # folder is filed in it, so a move by hand stands.
                folder = ensure_term_folder(session, course.get("term"))
                if folder is not None and workspace.folder_id is None:
                    workspace.folder_id = folder.id
                written = write_course(
                    session,
                    workspace.id,
                    course["id"],
                    snapshot,
                    fresh_workspace=fresh,
                )
                result = CourseResult(
                    course["id"], name, workspace.id, gone=written.gone
                )
                # Committed before queueing: the worker is another process and
                # would look for a row not yet written.
                session.commit()
            for document_id in written.to_read:
                ingest_document(document_id)

            for pending in written.pending_files:
                _fetch_and_keep(factory, result.workspace_id, pending, result, log)
            results.append(result)
    log.add("finished", classes=len(results), errors=log.errors)
    return results


def _fetch_and_keep(
    factory: sessionmaker[Session],
    workspace_id: int,
    pending: PendingFile,
    result: CourseResult,
    log: RunHandle,
) -> None:
    name = pending.ref.name
    try:
        data = download(pending.ref.url)
    except httpx.HTTPError:
        # One unreadable file must not stop the rest; the log says which.
        log.add("file_failed", "error", name=name)
        return
    with factory() as session:
        if pending.refresh is None:
            document_id = store_file(
                session, workspace_id, pending.folder_id, pending.ref, data
            )
            outcome = "file_kept" if document_id is not None else "file_skipped"
        else:
            title = refresh_file(session, pending.refresh, pending.ref, data)
            document_id = pending.refresh if title is not None else None
            if title is not None:
                result.refreshed.append(title)
            outcome = "file_updated" if title is not None else "file_skipped"
        session.commit()
    log.add(outcome, name=name)
    if document_id is not None:
        ingest_document(document_id)


def _name_of(course: dict) -> str:
    return course.get("name") or course.get("course_code") or f"Course {course['id']}"
