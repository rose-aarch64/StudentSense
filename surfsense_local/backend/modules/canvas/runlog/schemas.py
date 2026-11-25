from pydantic import BaseModel, ConfigDict

from modules.canvas.runlog.log import Param


class LogEntryRead(BaseModel):
    """One line of the log: a code and plain parameters, which the app words."""

    model_config = ConfigDict(from_attributes=True)

    n: int
    level: str
    code: str
    params: dict[str, Param]


class RunLogRead(BaseModel):
    """The last run's log, from the line after the one the reader has."""

    model_config = ConfigDict(from_attributes=True)

    run: int
    kind: str | None
    state: str
    entries: list[LogEntryRead]
    next: int
