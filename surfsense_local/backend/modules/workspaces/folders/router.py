from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from api.dependencies import SessionDep
from modules.workspaces.folders.schemas import WorkspaceFolderRead, WorkspaceFolderWrite
from modules.workspaces.models import WorkspaceFolder

router = APIRouter(prefix="/workspace-folders", tags=["workspaces"])


def _folder(session: SessionDep, folder_id: int) -> WorkspaceFolder:
    folder = session.get(WorkspaceFolder, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "folder not found")
    return folder


@router.get(
    "",
    response_model=list[WorkspaceFolderRead],
    summary="List workspace folders, oldest first",
)
def list_folders(session: SessionDep) -> Sequence[WorkspaceFolder]:
    return session.scalars(
        select(WorkspaceFolder).order_by(WorkspaceFolder.created_at, WorkspaceFolder.id)
    ).all()


@router.post(
    "",
    response_model=WorkspaceFolderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace folder",
)
def create_folder(
    payload: WorkspaceFolderWrite, session: SessionDep
) -> WorkspaceFolder:
    folder = WorkspaceFolder(name=payload.name)
    session.add(folder)
    # The id and timestamps come from the database, and the response needs them.
    session.flush()
    return folder


@router.patch(
    "/{folder_id}",
    response_model=WorkspaceFolderRead,
    summary="Rename a workspace folder",
)
def rename_folder(
    folder_id: int, payload: WorkspaceFolderWrite, session: SessionDep
) -> WorkspaceFolder:
    folder = _folder(session, folder_id)
    folder.name = payload.name
    return folder


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace folder; its workspaces are kept, unfiled",
)
def delete_folder(folder_id: int, session: SessionDep) -> Response:
    session.delete(_folder(session, folder_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
