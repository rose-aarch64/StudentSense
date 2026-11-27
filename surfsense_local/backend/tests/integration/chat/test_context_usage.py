"""How full a thread's history is, streamed with each reply and read on opening."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import Engine

from modules.chat.budget import (
    ANSWER_RESERVE_TOKENS,
    DEFAULT_HISTORY_TOKENS,
    EXCERPTS_TOKENS,
    IMAGE_TOKENS,
    QUESTION_TOKENS,
    SYSTEM_PROMPT_TOKENS,
    history_budget,
)
from modules.agent.context_use.last_prompt import forget_all, note_prompt
from modules.agent.model_window import FALLBACK_WINDOW, selected_model_window
from modules.agent.opencode_config import compaction_point
from modules.chat.models import AgentEngineKind, ChatThread
from modules.workspaces.models import Workspace
from shared.db import create_session_factory
from tests.integration.chat.conftest import (
    RemoteEndpoint,
    set_props_n_ctx,
    set_sees,
    set_tokens_per_word,
)
from tests.integration.chat.test_chat import (
    _open_thread,
    _seed,
    _seed_for_remote,
    _send,
)
from tests.integration.chat.test_images import picture

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def no_prompts_kept() -> None:
    """The agent's prompt sizes live in the process, so each test starts with none."""
    forget_all()

FIXED = SYSTEM_PROMPT_TOKENS + EXCERPTS_TOKENS + QUESTION_TOKENS + ANSWER_RESERVE_TOKENS


def _usage(events: list[dict]) -> list[dict]:
    return [event for event in events if event["type"] == "context-usage"]


async def test_a_reply_streams_context_usage_before_and_after(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    set_props_n_ctx(FIXED + 4000)
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)

    events = await _send(client, thread_id, "what happened to revenue?")

    before, after = _usage(events)
    types = [event["type"] for event in events]
    assert events.index(before) < types.index("delta")
    assert events.index(after) > len(types) - 1 - types[::-1].index("delta")
    assert events.index(after) < types.index("completed")
    assert before["used"] == 0
    assert after["used"] > before["used"]
    assert before["budget"] == after["budget"] == 4000


async def test_the_turns_own_pictures_come_out_of_the_budget_it_streams(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    """The trim pays for the turn's pictures out of history, so the gauge's 100%
    moves with them."""
    set_props_n_ctx(FIXED + 4000)
    set_sees(True)
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)

    events: list[dict] = []
    async with client.stream(
        "POST",
        f"/chat/threads/{thread_id}/messages",
        json={"text": "what is this?", "images": [picture()]},
    ) as reply:
        async for line in reply.aiter_lines():
            if line.startswith("data: {"):
                events.append(json.loads(line[len("data: ") :]))

    before, _after = _usage(events)
    assert before["budget"] == 4000 - IMAGE_TOKENS


async def test_a_remote_llama_server_is_measured_against_its_own_window(
    client: AsyncClient,
    engine: Engine,
    real_model: object,
    remote_endpoint: RemoteEndpoint,
) -> None:
    """An openai_compatible connection pointing at a llama-server reports its
    window at /props, so history is budgeted from it and not the fixed figure."""
    remote_endpoint.props_n_ctx = FIXED + 4000
    workspace_id = _seed_for_remote(engine)
    thread_id = await _open_thread(client, workspace_id)

    events = await _send(client, thread_id, "what happened to revenue?")

    assert {frame["budget"] for frame in _usage(events)} == {4000}


async def test_a_remote_llama_servers_replies_are_not_capped_by_its_window(
    client: AsyncClient,
    engine: Engine,
    real_model: object,
    remote_endpoint: RemoteEndpoint,
) -> None:
    """Knowing the window must not start capping replies at the answer reserve,
    which would cut a thinking model off before its answer."""
    remote_endpoint.props_n_ctx = FIXED + 4000
    workspace_id = _seed_for_remote(engine)
    thread_id = await _open_thread(client, workspace_id)

    await _send(client, thread_id, "what happened to revenue?")

    answer = next(
        request for request in remote_endpoint.requests if request.get("max_tokens") != 12
    )
    assert answer.get("max_tokens") is None


async def test_the_agent_keeps_its_fallback_window_whatever_a_llama_server_reports(
    engine: Engine, remote_endpoint: RemoteEndpoint
) -> None:
    """Given the real 16,384, opencode would summarise at 12,288, but its own
    instructions and tools take about 12,000 of that, so it could never get
    under. A turn that read a 13,000-character note stalled on it."""
    remote_endpoint.props_n_ctx = 16384

    with create_session_factory(engine)() as session:
        assert await selected_model_window(session) == (
            "remote-model",
            FALLBACK_WINDOW,
        )


async def test_an_endpoint_that_reports_no_window_keeps_the_agents_fallback(
    engine: Engine, remote_endpoint: RemoteEndpoint
) -> None:
    with create_session_factory(engine)() as session:
        assert await selected_model_window(session) == (
            "remote-model",
            FALLBACK_WINDOW,
        )


async def test_a_remote_endpoint_with_no_props_keeps_the_fixed_budget(
    client: AsyncClient,
    engine: Engine,
    real_model: object,
    remote_endpoint: RemoteEndpoint,
) -> None:
    workspace_id = _seed_for_remote(engine)
    thread_id = await _open_thread(client, workspace_id)

    events = await _send(client, thread_id, "what happened to revenue?")

    assert {frame["budget"] for frame in _usage(events)} == {DEFAULT_HISTORY_TOKENS}


async def test_a_gauge_that_cannot_be_read_never_costs_the_reply_its_end(
    client: AsyncClient,
    engine: Engine,
    real_model: object,
    llamacpp_server: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_props_n_ctx(FIXED + 4000)
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)

    def unreadable(*_args: object) -> None:
        raise RuntimeError("the database went away")

    monkeypatch.setattr("modules.chat.router._stored_turns", unreadable)

    events = await _send(client, thread_id, "what happened to revenue?")

    assert events[-1]["type"] == "completed"
    assert len(_usage(events)) == 1


async def test_a_reply_on_an_unknown_window_streams_the_fallback_budget(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    """An endpoint that reports no window is trimmed at a fixed history budget,
    and that is where the gauge reaches 100%."""
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)

    events = await _send(client, thread_id, "what happened to revenue?")

    assert {frame["budget"] for frame in _usage(events)} == {DEFAULT_HISTORY_TOKENS}


async def test_a_trimmed_thread_reports_the_settled_figure(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    """Past the budget the next turn cuts history to 75% of it, so the gauge
    falls back before it climbs again."""
    set_props_n_ctx(FIXED + 40)
    set_tokens_per_word(1)
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)

    runs = [
        _usage(await _send(client, thread_id, f"question number {n} about revenue"))
        for n in range(6)
    ]

    settled = [
        later[0]["used"]
        for earlier, later in zip(runs, runs[1:], strict=False)
        if later[0]["used"] < earlier[-1]["used"]
    ]
    assert settled
    assert all(used <= 0.75 * 40 for used in settled)


async def test_context_usage_endpoint_reads_a_stored_thread(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    set_props_n_ctx(FIXED + 4000)
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)
    await _send(client, thread_id, "what happened to revenue?")

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.status_code == 200
    assert reply.json()["used"] > 0
    assert reply.json()["budget"] == history_budget(FIXED + 4000) == 4000


async def test_context_usage_endpoint_uses_the_fallback_budget_for_an_unknown_window(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.json() == {"used": 0, "budget": DEFAULT_HISTORY_TOKENS}


async def test_context_usage_endpoint_has_no_budget_for_an_agent_thread(
    client: AsyncClient, engine: Engine, real_model: object, llamacpp_server: list[dict]
) -> None:
    set_props_n_ctx(FIXED + 4000)
    workspace_id, _ids = _seed(engine)
    thread_id = await _open_thread(client, workspace_id)
    with create_session_factory(engine)() as session:
        session.get(ChatThread, thread_id).agent_engine = AgentEngineKind.OPENCODE
        session.commit()

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.json()["budget"] is None


def _agent_thread(engine: Engine, kind: AgentEngineKind, session_id: str | None) -> int:
    with create_session_factory(engine)() as session:
        workspace = Workspace(name="Notes")
        session.add(workspace)
        session.flush()
        thread = ChatThread(
            workspace_id=workspace.id,
            title="Agent",
            agent_engine=kind,
            opencode_session_id=session_id,
        )
        session.add(thread)
        session.commit()
        return thread.id


async def test_an_agent_thread_is_measured_against_the_window_the_server_reports(
    client: AsyncClient, engine: Engine, remote_endpoint: RemoteEndpoint
) -> None:
    """opencode is told a larger window than the server has, so 100% is where
    the server would refuse the next request, not where opencode summarises."""
    remote_endpoint.props_n_ctx = 16384
    thread_id = _agent_thread(engine, AgentEngineKind.OPENCODE, "ses_gauge")
    note_prompt("ses_gauge", 5120)

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.json() == {"used": 5120, "budget": 16384}


async def test_an_agent_thread_with_no_reported_window_uses_the_compaction_point(
    client: AsyncClient, engine: Engine, remote_endpoint: RemoteEndpoint
) -> None:
    thread_id = _agent_thread(engine, AgentEngineKind.OPENCODE, "ses_gauge")
    note_prompt("ses_gauge", 5120)

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.json() == {
        "used": 5120,
        "budget": compaction_point(FALLBACK_WINDOW),
    }


async def test_an_agent_session_that_has_sent_nothing_is_not_measured(
    client: AsyncClient, engine: Engine, remote_endpoint: RemoteEndpoint
) -> None:
    """After a restart the app has no figure until the session's next step."""
    remote_endpoint.props_n_ctx = 16384
    thread_id = _agent_thread(engine, AgentEngineKind.OPENCODE, "ses_unheard")

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.json() == {"used": 0, "budget": None}


async def test_a_claude_code_thread_is_not_measured(
    client: AsyncClient, engine: Engine, remote_endpoint: RemoteEndpoint
) -> None:
    """Its turns do not pass the model relay, so there is no figure to show."""
    remote_endpoint.props_n_ctx = 16384
    thread_id = _agent_thread(engine, AgentEngineKind.CLAUDE_CODE, "ses_gauge")
    note_prompt("ses_gauge", 5120)

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.json() == {"used": 0, "budget": None}


async def test_context_usage_endpoint_with_no_model_selected_has_no_budget(
    client: AsyncClient, engine: Engine
) -> None:
    with create_session_factory(engine)() as session:
        workspace = Workspace(name="Notes")
        session.add(workspace)
        session.commit()
        workspace_id = workspace.id
    thread_id = await _open_thread(client, workspace_id)

    reply = await client.get(f"/chat/threads/{thread_id}/context-usage")

    assert reply.status_code == 200
    assert reply.json() == {"used": 0, "budget": None}
