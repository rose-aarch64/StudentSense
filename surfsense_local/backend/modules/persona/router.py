from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from modules.persona.store import (
    agent_persona_text,
    persona_text,
    save_agent_persona,
    save_persona,
)

router = APIRouter(prefix="/persona", tags=["persona"])


class PersonaBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A style note rides in every prompt, so it is kept short of a window's worth.
    text: str = Field(max_length=20_000)


@router.get("", response_model=PersonaBody, summary="Read the persona text")
def read_persona() -> PersonaBody:
    return PersonaBody(text=persona_text())


@router.put("", response_model=PersonaBody, summary="Replace the persona text")
def write_persona(payload: PersonaBody) -> PersonaBody:
    save_persona(payload.text)
    return PersonaBody(text=persona_text())


@router.get(
    "/agent",
    response_model=PersonaBody,
    summary="Read the agent's own persona text, empty when it uses the shared one",
)
def read_agent_persona() -> PersonaBody:
    return PersonaBody(text=agent_persona_text())


@router.put(
    "/agent",
    response_model=PersonaBody,
    summary="Replace the agent's own persona text",
)
def write_agent_persona(payload: PersonaBody) -> PersonaBody:
    save_agent_persona(payload.text)
    return PersonaBody(text=agent_persona_text())
