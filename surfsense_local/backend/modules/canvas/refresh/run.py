from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from modules.canvas import links
from modules.canvas.client import (
    CanvasClient,
    CanvasNotFoundError,
    CanvasRefusedError,
    CanvasUnreachableError,
)
from modules.canvas.models import CanvasConnection
from modules.canvas.sync.connection import NotConnectedError, read_connection
from modules.canvas.sync.tasks import sync_tasks
from modules.canvas.sync.term import courses_to_sync
from modules.egress.service import EgressDeniedError
from modules.workspaces.models import Workspace
from shared.secrets import UnreadableSecretError

NOT_CONNECTED = "canvas_not_connected"
# What can stop a pass, as the code Settings words for the user.
_FAILURES: tuple[tuple[type[Exception], str], ...] = (
    (UnreadableSecretError, "canvas_token_unreadable"),
    (CanvasRefusedError, "canvas_token_refused"),
    (CanvasUnreachableError, "canvas_unreachable"),
    (EgressDeniedError, "egress_disabled"),
)


@dataclass(frozen=True)
class RefreshResult:
    # Classes whose tasks were brought in line with Canvas.
    classes: int
    # The code recorded for a pass that could not run, else None.
    error: str | None


def refresh_tasks(
    factory: sessionmaker[Session], now: datetime | None = None
) -> RefreshResult:
    """Bring the tasks of every synced class of the current term in line with Canvas.

    Only assignments are read, and only tasks written: a class with no workspace
    yet is left for a full sync. A pass that cannot run records why on the
    connection and changes no task.
    """
    now = now or datetime.now(UTC)
    try:
        classes = _refresh(factory, now)
    except NotConnectedError:
        return RefreshResult(0, NOT_CONNECTED)  # no connection row to record on
    except tuple(kind for kind, _ in _FAILURES) as failure:
        code = next(code for kind, code in _FAILURES if isinstance(failure, kind))
        _record(factory, refreshed_at=None, error=code)
        return RefreshResult(0, code)
    _record(factory, refreshed_at=now, error=None)
    return RefreshResult(classes, None)


def _refresh(factory: sessionmaker[Session], now: datetime) -> int:
    base_url, token = read_connection(factory)
    # Canvas is read with no session open, so a slow answer never holds the
    # database's write lock.
    fetched: list[tuple[int, list[dict]]] = []
    with CanvasClient(base_url, token) as canvas:
        courses = canvas.get_all(
            "/courses", {"enrollment_state": "active", "include[]": "term"}
        )
        current = courses_to_sync(courses, None, now)
        workspaces = _workspaces_of(factory, [course["id"] for course in current])
        for course in current:
            if course["id"] not in workspaces:
                continue
            try:
                assignments = canvas.get_all(
                    f"/courses/{course['id']}/assignments", {"include[]": "submission"}
                )
            except CanvasNotFoundError:
                continue  # a course gone from Canvas must not stop the others
            fetched.append((workspaces[course["id"]], assignments))
    return sum(_write(factory, workspace_id, a) for workspace_id, a in fetched)


def _workspaces_of(
    factory: sessionmaker[Session], course_ids: list[int]
) -> dict[int, int]:
    """The workspace each synced course became; a link to a deleted one is not."""
    found: dict[int, int] = {}
    with factory() as session:
        for course_id in course_ids:
            local_id = links.linked_id(session, links.COURSE, course_id)
            if local_id is not None and session.get(Workspace, local_id) is not None:
                found[course_id] = local_id
    return found


def _write(
    factory: sessionmaker[Session], workspace_id: int, assignments: list[dict]
) -> bool:
    """One class in one short transaction; false when a racing sync got there first."""
    with factory() as session:
        try:
            sync_tasks(session, workspace_id, assignments, revive=False)
            session.commit()
        except IntegrityError:
            session.rollback()
            return False
    return True


def _record(
    factory: sessionmaker[Session], *, refreshed_at: datetime | None, error: str | None
) -> None:
    with factory() as session:
        row = session.get(CanvasConnection, 1)
        if row is None:
            return  # disconnected while the pass ran
        if error is None:
            row.refreshed_at = refreshed_at
        row.refresh_error = error
        session.commit()
