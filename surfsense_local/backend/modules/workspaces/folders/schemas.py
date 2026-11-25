from datetime import datetime

from pydantic import BaseModel, ConfigDict

from modules.workspaces.schemas import WorkspaceName


class WorkspaceFolderWrite(BaseModel):
    """A folder's name, for creating one and for renaming it."""

    model_config = ConfigDict(extra="forbid")

    name: WorkspaceName


class WorkspaceFolderRead(BaseModel):
    """A folder as the API returns it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
