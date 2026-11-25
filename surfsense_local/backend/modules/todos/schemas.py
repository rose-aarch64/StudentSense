from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    PositiveInt,
    StringConstraints,
    computed_field,
    model_validator,
)

from modules.todos.models import TodoSource

# Stripped before the length check, so a title of spaces fails rather than
# becoming a row the list renders as blank.
TodoTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class TodoCreate(BaseModel):
    """A task the user writes. A source's tasks are made by its sync, not here."""

    model_config = ConfigDict(extra="forbid")

    title: TodoTitle
    due_at: datetime | None = None
    workspace_id: PositiveInt | None = None


class TodoUpdate(BaseModel):
    """Fields a client may change. Unset fields are left alone; a null `due_at`
    clears the date."""

    model_config = ConfigDict(extra="forbid")

    title: TodoTitle | None = None
    due_at: datetime | None = None
    done: bool | None = None

    @model_validator(mode="after")
    def _title_is_never_cleared(self) -> Self:
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")
        if "done" in self.model_fields_set and self.done is None:
            raise ValueError("done cannot be null")
        return self


class TodoRead(BaseModel):
    """A task as the API returns it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int | None
    title: str
    due_at: datetime | None
    done_at: datetime | None
    source: TodoSource
    source_key: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def done(self) -> bool:
        return self.done_at is not None
