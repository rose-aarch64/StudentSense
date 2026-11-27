import logging

from sqlalchemy.orm import Session

from api.dependencies import transact
from modules.agent.context_use.last_prompt import last_prompt
from modules.agent.model_window import selected_model_window, selected_text_model
from modules.agent.opencode_config import compaction_point
from modules.chat.models import AgentEngineKind, ChatThread
from modules.llm.providers import llamacpp
from modules.llm.resolution import ModelResolutionError, resolve_generation

logger = logging.getLogger(__name__)


def agent_budget(configured: int, reported: int | None) -> int:
    """Where an agent thread's gauge reaches 100%.

    opencode summarises at its compaction point, but it is told a window that
    can be larger than the server's own, which refuses a request past it
    before opencode would act, so whichever comes first.
    """
    point = compaction_point(configured)
    return point if reported is None else min(point, reported)


async def agent_usage(session: Session, thread: ChatThread) -> tuple[int, int | None]:
    """How full an agent thread's memory is: the prompt its session last sent,
    against where it runs out. No budget until the session has sent a step
    since the app started, and for an engine whose turns do not pass the model
    relay."""
    if thread.agent_engine is not AgentEngineKind.OPENCODE:
        return 0, None
    used = last_prompt(thread.opencode_session_id)
    if used is None:
        return 0, None
    try:
        _model, configured = await selected_model_window(session)
        reported = await _reported_window(session)
    except ModelResolutionError:
        return 0, None
    return used, agent_budget(configured, reported)


async def _reported_window(session: Session) -> int | None:
    """The window the server behind the selected model reports, if it does.

    A local runtime's is already the configured one, and asking it can load the
    model, so only another connection is asked.
    """
    selected, _catalog = await transact(session, selected_text_model)
    if selected.provider == llamacpp.PROVIDER:
        return None
    try:
        resolved = await transact(session, resolve_generation)
        return await resolved.generator.context_tokens(selected.name)
    except ModelResolutionError:
        raise
    except Exception:
        logger.warning("could not read the endpoint's window", exc_info=True)
        return None
