from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from modules.canvas import links
from modules.canvas.client import CanvasClient
from modules.canvas.runlog.log import NULL_HANDLE, RunHandle
from modules.canvas.sync.attachments_folder import ATTACHMENTS
from modules.canvas.sync.connection import read_connection
from modules.canvas.sync.files import changed_titles, gone_titles
from modules.canvas.sync.snapshot import read_file_refs
from modules.canvas.sync.term import courses_to_sync


@dataclass(frozen=True)
class StaleCourse:
    canvas_id: int
    name: str
    workspace_id: int
    # Kept files Canvas has since edited.
    changed: list[str]
    # Kept files Canvas no longer lists.
    gone: list[str]


def check_stale(
    factory: sessionmaker[Session],
    term: str | None = None,
    log: RunHandle = NULL_HANDLE,
) -> list[StaleCourse]:
    """Which kept files no longer match Canvas, asking Canvas only about the
    files themselves: no bytes are fetched, and nothing is written or queued.

    A course never synced has no workspace to compare, and is left out. Each
    class compared is written to `log`.
    """
    log.add("check_started")
    base_url, token = read_connection(factory)

    checked: list[StaleCourse] = []
    with CanvasClient(base_url, token) as canvas:
        courses = canvas.get_all(
            "/courses", {"enrollment_state": "active", "include[]": "term"}
        )
        for course in courses_to_sync(courses, term, datetime.now(UTC)):
            with factory() as session:
                workspace_id = links.linked_id(session, links.COURSE, course["id"])
            if workspace_id is None:
                continue
            refs = read_file_refs(canvas, course["id"])
            with factory() as session:
                compared = StaleCourse(
                    canvas_id=course["id"],
                    name=_name_of(course),
                    workspace_id=workspace_id,
                    changed=changed_titles(session, refs),
                    # Only module files are read here, so files the text links
                    # to are not ones this check could find missing.
                    gone=gone_titles(
                        session,
                        workspace_id,
                        {ref.file_id for ref in refs},
                        links.linked_id(session, ATTACHMENTS, course["id"]),
                    ),
                )
            checked.append(compared)
            log.add(
                "class_checked",
                name=compared.name,
                changed=len(compared.changed),
                gone=len(compared.gone),
            )
    log.add("finished", classes=len(checked), errors=log.errors)
    return checked


def _name_of(course: dict) -> str:
    return course.get("name") or course.get("course_code") or f"Course {course['id']}"
