from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

QuestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    text: str = ""


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: QuestionText
    # With its zone: the server does not know which day the user is living in.
    now: AwareDatetime
    # The window keeps its own conversation; nothing is stored here.
    history: list[Turn] = []


class AskReply(BaseModel):
    text: str
