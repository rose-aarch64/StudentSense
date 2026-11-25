from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Token = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ConnectionWrite(BaseModel):
    """What the user enters: the school's address and a Canvas access token."""

    model_config = ConfigDict(extra="forbid")

    base_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    token: Token


class SyncRequest(BaseModel):
    """What to sync: every active course, or only those of one term."""

    model_config = ConfigDict(extra="forbid")

    term: str | None = None


class SyncedCourse(BaseModel):
    canvas_id: int
    name: str
    workspace_id: int
    # Files edited in Canvas whose kept copy was replaced.
    refreshed: list[str] = []
    # Kept files Canvas no longer lists; left in place.
    gone: list[str] = []


class SyncResult(BaseModel):
    courses: list[SyncedCourse]


class StaleCourseRead(BaseModel):
    canvas_id: int
    name: str
    workspace_id: int
    changed: list[str]
    gone: list[str]


class StaleResult(BaseModel):
    courses: list[StaleCourseRead]


class ConnectionStatus(BaseModel):
    """The connection as the API shows it. The token is never part of it."""

    connected: bool
    base_url: str | None = None
    user_name: str | None = None
    auto_refresh: bool = False
    # When the last refresh pass succeeded, and how the last one failed, as a code.
    refreshed_at: datetime | None = None
    refresh_error: str | None = None


class ConnectionPatch(BaseModel):
    """What the user may change on a saved connection."""

    model_config = ConfigDict(extra="forbid")

    auto_refresh: bool
