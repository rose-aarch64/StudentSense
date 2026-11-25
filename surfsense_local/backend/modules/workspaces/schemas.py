from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    PositiveInt,
    StringConstraints,
    model_validator,
)

# Stripped before the length check, so a name of spaces fails rather than
# becoming a row the switcher renders as blank.
WorkspaceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
# A key into the interface's icon set. It stays a plain slug so a later release
# can add icons without a migration.
IconKey = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{1,32}$")]


class WorkspaceCreate(BaseModel):
    """Fields a client supplies when opening a workspace."""

    name: WorkspaceName


class WorkspaceUpdate(BaseModel):
    """Fields a client may change. Unset fields are left alone; a null `icon` or
    `folder_id` clears it."""

    model_config = ConfigDict(extra="forbid")

    name: WorkspaceName | None = None
    icon: IconKey | None = None
    folder_id: PositiveInt | None = None

    @model_validator(mode="after")
    def _names_something_and_never_clears_the_name(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("nothing to change")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class WorkspaceRead(BaseModel):
    """A workspace as the API returns it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str | None
    folder_id: int | None
    created_at: datetime
    updated_at: datetime
