from fastapi import APIRouter, HTTPException, status

from api.dependencies import SessionDep, transact
from modules.llm.activity import ModelBusyError, model_activity, model_key
from modules.llm.providers.types import Message
from modules.llm.resolution import ModelResolutionError, resolve_generation
from modules.persona.apply import with_persona
from modules.persona.store import persona_text
from modules.today.open_tasks import load_open_tasks
from modules.today.picture import day_picture
from modules.today.schemas import AskReply, AskRequest

router = APIRouter(prefix="/today", tags=["today"])

# The window reads the list and never writes it, so it says so rather than
# pretend when asked to.
INSTRUCTION = """You help the user plan their day from the task list below.

- Use only the date and the tasks given. Never invent a task, a class or a due time.
- Start with what is happening today, then what is overdue. Then suggest an order for the work, with rough blocks of time, putting what is due soonest first.
- You can only read the list. If asked to add, move or finish a task, say you cannot yet and say what to do in the to-do list instead.
- Be brief. Answer in the language of the question."""


def _ground(session: SessionDep, payload: AskRequest):
    """Everything the answer needs from the database, read in one stretch."""
    resolved = resolve_generation(session)
    picture = day_picture(load_open_tasks(session), payload.now)
    return resolved, picture


@router.post("/ask", response_model=AskReply, summary="Ask about today")
async def ask(payload: AskRequest, session: SessionDep) -> AskReply:
    try:
        resolved, picture = await transact(session, _ground, payload)
    except ModelResolutionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    system = with_persona(f"{INSTRUCTION}\n\n{picture}", persona_text())
    messages = [
        Message("system", system),
        *(Message(turn.role, turn.text) for turn in payload.history),
        Message("user", payload.text),
    ]
    selected = resolved.selection
    key = model_key(selected.provider, selected.name, selected.connection_id)
    try:
        await model_activity.acquire_use(key)
    except ModelBusyError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    try:
        parts = [
            delta async for delta in resolved.generator.chat(selected.name, messages)
        ]
    finally:
        await model_activity.release_use(key)
    return AskReply(text="".join(parts).strip())
