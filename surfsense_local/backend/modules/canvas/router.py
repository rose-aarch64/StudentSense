from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from api.dependencies import SessionDep
from modules.canvas.address import CanvasAddressError, school_origin
from modules.canvas.client import (
    CanvasClient,
    CanvasRefusedError,
    CanvasUnreachableError,
)
from modules.canvas.consent import require_school
from modules.canvas.models import CanvasConnection
from modules.canvas.runlog.logged_run import logged
from modules.canvas.runlog.schemas import RunLogRead
from modules.canvas.schemas import (
    ConnectionPatch,
    ConnectionStatus,
    ConnectionWrite,
    StaleCourseRead,
    StaleResult,
    SyncedCourse,
    SyncRequest,
    SyncResult,
)
from modules.canvas.sync.connection import NotConnectedError
from modules.canvas.sync.run import run_sync
from modules.canvas.sync.stale import check_stale
from shared.secrets import UnreadableSecretError, encrypt

router = APIRouter(prefix="/canvas", tags=["canvas"])


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code, {"code": code, "message": message})


def _status(row: CanvasConnection | None) -> ConnectionStatus:
    if row is None:
        return ConnectionStatus(connected=False)
    return ConnectionStatus(
        connected=True,
        base_url=row.base_url,
        user_name=row.user_name,
        auto_refresh=row.auto_refresh,
        refreshed_at=row.refreshed_at,
        refresh_error=row.refresh_error,
    )


@router.get(
    "/connection",
    response_model=ConnectionStatus,
    summary="Whether Canvas is connected",
)
def read_connection(session: SessionDep) -> ConnectionStatus:
    return _status(session.get(CanvasConnection, 1))


@router.put(
    "/connection",
    response_model=ConnectionStatus,
    summary="Connect a school's Canvas with an access token",
)
def connect(payload: ConnectionWrite, session: SessionDep) -> ConnectionStatus:
    try:
        base_url = school_origin(payload.base_url)
    except CanvasAddressError as bad:
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, bad.code, str(bad)) from bad

    require_school(session, base_url)

    try:
        with CanvasClient(base_url, payload.token) as canvas:
            me = canvas.get_one("/users/self")
    except CanvasRefusedError as refused_token:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "canvas_token_refused",
            "Canvas did not accept that token",
        ) from refused_token
    except CanvasUnreachableError as unreachable:
        raise _error(
            status.HTTP_502_BAD_GATEWAY,
            "canvas_unreachable",
            "Canvas could not be reached",
        ) from unreachable

    row = session.get(CanvasConnection, 1) or CanvasConnection(id=1)
    row.base_url = base_url
    row.token_ciphertext = encrypt(payload.token)
    row.user_name = me.get("name")
    # A new token may be the fix for a refused one; the setting itself stays.
    row.refresh_error = None
    session.add(row)
    session.flush()
    return _status(row)


@router.patch(
    "/connection",
    response_model=ConnectionStatus,
    summary="Change a saved connection's settings",
)
def change_connection(
    payload: ConnectionPatch, session: SessionDep
) -> ConnectionStatus:
    row = session.get(CanvasConnection, 1)
    if row is None:
        raise _error(
            status.HTTP_409_CONFLICT, "canvas_not_connected", "Canvas is not connected"
        )
    row.auto_refresh = payload.auto_refresh
    session.flush()
    return _status(row)


@router.delete(
    "/connection",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect Canvas and forget its token",
)
def disconnect(session: SessionDep) -> Response:
    row = session.get(CanvasConnection, 1)
    if row is not None:
        session.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sync",
    response_model=SyncResult,
    summary="Read Canvas and bring the workspaces in line with it",
)
def sync(payload: SyncRequest, request: Request) -> SyncResult:
    handle = request.app.state.canvas_log.start("sync")
    with _canvas_errors(), logged(handle):
        courses = run_sync(request.app.state.session_factory, payload.term, handle)

    return SyncResult(
        courses=[
            SyncedCourse(
                canvas_id=c.canvas_id,
                name=c.name,
                workspace_id=c.workspace_id,
                refreshed=c.refreshed,
                gone=c.gone,
            )
            for c in courses
        ]
    )


@router.get(
    "/log",
    response_model=RunLogRead,
    summary="What the last Sync or Check read, kept and failed on",
)
def read_log(
    request: Request, run: int | None = None, after: Annotated[int, Query(ge=0)] = 0
) -> RunLogRead:
    return RunLogRead.model_validate(request.app.state.canvas_log.read(run, after))


@router.get(
    "/stale",
    response_model=StaleResult,
    summary="Which kept files no longer match Canvas, changing nothing",
)
def stale(request: Request, term: str | None = None) -> StaleResult:
    handle = request.app.state.canvas_log.start("check")
    with _canvas_errors(), logged(handle):
        courses = check_stale(request.app.state.session_factory, term, handle)

    return StaleResult(
        courses=[
            StaleCourseRead(
                canvas_id=c.canvas_id,
                name=c.name,
                workspace_id=c.workspace_id,
                changed=c.changed,
                gone=c.gone,
            )
            for c in courses
        ]
    )


@contextmanager
def _canvas_errors() -> Iterator[None]:
    """What can go wrong reading Canvas, as the answers the app understands."""
    try:
        yield
    except NotConnectedError as missing:
        raise _error(
            status.HTTP_409_CONFLICT, "canvas_not_connected", "Canvas is not connected"
        ) from missing
    except UnreadableSecretError as unreadable:
        raise _error(
            status.HTTP_409_CONFLICT,
            "canvas_token_unreadable",
            "The saved token cannot be read on this computer; connect Canvas again",
        ) from unreadable
    except CanvasRefusedError as refused:
        # Not 401: the app reads that as its own sign-in having lapsed.
        raise _error(
            status.HTTP_409_CONFLICT,
            "canvas_token_refused",
            "Canvas no longer accepts the saved token; connect Canvas again",
        ) from refused
    except CanvasUnreachableError as unreachable:
        raise _error(
            status.HTTP_502_BAD_GATEWAY,
            "canvas_unreachable",
            "Canvas could not be reached",
        ) from unreachable
