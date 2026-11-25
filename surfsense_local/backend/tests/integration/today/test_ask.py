from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from modules.llm.providers.types import Message
from modules.llm.resolution import ModelResolutionError

pytestmark = pytest.mark.integration

NOW = "2026-11-24T09:30:00-05:00"


class Recorder:
    """Stands in for the selected model and keeps what it was sent."""

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def chat(
        self, model: str, messages: list[Message], **_: object
    ) -> AsyncIterator[str]:
        self.sent = messages
        for part in ("Two things ", "today."):
            yield part


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    """The route's chat model, replaced by one that records its prompt."""
    recorder = Recorder()
    selection = SimpleNamespace(provider="test", name="m", connection_id=None)
    monkeypatch.setattr(
        "modules.today.router.resolve_generation",
        lambda session: SimpleNamespace(selection=selection, generator=recorder),
    )
    return recorder


async def test_the_model_is_given_the_date_and_every_workspaces_tasks(
    client: AsyncClient, model: Recorder
) -> None:
    """One question, answered from all the classes at once."""
    bio = (await client.post("/workspaces", json={"name": "Bio"})).json()["id"]
    await client.post(
        "/todos",
        json={"title": "Lab 1", "due_at": "2026-11-24T23:00:00Z", "workspace_id": bio},
    )
    await client.post("/todos", json={"title": "Call the bursar"})

    reply = await client.post(
        "/today/ask", json={"text": "what's going on today?", "now": NOW}
    )

    assert reply.status_code == 200
    assert reply.json() == {"text": "Two things today."}
    system = model.sent[0]
    assert system.role == "system"
    assert "Tuesday, November 24, 2026" in system.content
    assert "[Bio] Lab 1" in system.content
    assert "Call the bursar" in system.content
    assert model.sent[-1] == Message("user", "what's going on today?")


async def test_a_finished_task_is_not_part_of_the_day(
    client: AsyncClient, model: Recorder
) -> None:
    """A checked-off task is not something to schedule."""
    done = await client.post("/todos", json={"title": "Already done"})
    await client.patch(f"/todos/{done.json()['id']}", json={"done": True})

    await client.post("/today/ask", json={"text": "plan my day", "now": NOW})

    assert "Already done" not in model.sent[0].content


async def test_the_persona_rides_after_the_rules_and_earlier_turns_are_kept(
    client: AsyncClient, model: Recorder
) -> None:
    """The window remembers its own conversation; the server does not."""
    await client.put("/persona", json={"text": "Call me Rose."})

    await client.post(
        "/today/ask",
        json={
            "text": "and tomorrow?",
            "now": NOW,
            "history": [
                {"role": "user", "text": "what's today?"},
                {"role": "assistant", "text": "Nothing."},
            ],
        },
    )

    assert model.sent[0].content.endswith("Call me Rose.")
    assert [m.role for m in model.sent] == ["system", "user", "assistant", "user"]


async def test_no_chat_model_selected_says_so(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window cannot answer without a model, and the user is told why."""

    def none_selected(session: object) -> object:
        raise ModelResolutionError("no chat model selected")

    monkeypatch.setattr("modules.today.router.resolve_generation", none_selected)

    reply = await client.post("/today/ask", json={"text": "hi", "now": NOW})

    assert reply.status_code == 409
    assert "no chat model selected" in reply.text


async def test_a_time_with_no_zone_is_refused(client: AsyncClient) -> None:
    """Without the user's zone, today could be the wrong day."""
    reply = await client.post(
        "/today/ask", json={"text": "hi", "now": "2026-11-24T09:30:00"}
    )

    assert reply.status_code == 422
