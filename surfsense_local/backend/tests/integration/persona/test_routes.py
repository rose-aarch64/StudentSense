import pytest
from httpx import AsyncClient

from modules.persona.store import agent_persona_text, persona_text

pytestmark = pytest.mark.integration


async def test_a_new_install_has_no_persona(client: AsyncClient) -> None:
    """Until one is written, models speak in their own voice."""
    response = await client.get("/persona")

    assert response.status_code == 200
    assert response.json() == {"text": ""}


async def test_a_saved_persona_is_read_back(client: AsyncClient) -> None:
    """The settings box and the prompt builder read the same text."""
    saved = await client.put("/persona", json={"text": "Be brief. Call me Rose."})

    assert saved.status_code == 200
    assert (await client.get("/persona")).json() == {"text": "Be brief. Call me Rose."}
    assert persona_text() == "Be brief. Call me Rose."


async def test_saving_nothing_clears_the_persona(client: AsyncClient) -> None:
    """Emptying the box is how the user turns the persona off."""
    await client.put("/persona", json={"text": "Be brief."})

    await client.put("/persona", json={"text": "  \n"})

    assert (await client.get("/persona")).json() == {"text": ""}


async def test_a_persona_too_long_to_be_a_style_note_is_refused(
    client: AsyncClient,
) -> None:
    """A style note rides in every prompt, so a pasted book is turned away."""
    response = await client.put("/persona", json={"text": "x" * 20_001})

    assert response.status_code == 422


async def test_a_new_install_has_no_agent_persona(client: AsyncClient) -> None:
    """Until one is written, the agent uses the shared persona."""
    response = await client.get("/persona/agent")

    assert response.status_code == 200
    assert response.json() == {"text": ""}


async def test_an_agent_persona_is_kept_apart_from_the_shared_one(
    client: AsyncClient,
) -> None:
    """Writing the agent's note leaves the chat's note as it was."""
    await client.put("/persona", json={"text": "Long voice."})

    saved = await client.put("/persona/agent", json={"text": "Short voice."})

    assert saved.status_code == 200
    assert (await client.get("/persona/agent")).json() == {"text": "Short voice."}
    assert (await client.get("/persona")).json() == {"text": "Long voice."}
    assert agent_persona_text() == "Short voice."


async def test_saving_nothing_clears_the_agent_persona(client: AsyncClient) -> None:
    """Emptying the box sends the agent back to the shared persona."""
    await client.put("/persona/agent", json={"text": "Short voice."})

    await client.put("/persona/agent", json={"text": "  \n"})

    assert (await client.get("/persona/agent")).json() == {"text": ""}


async def test_an_agent_persona_too_long_to_be_a_style_note_is_refused(
    client: AsyncClient,
) -> None:
    """The agent's note rides in every agent prompt, so it has the same limit."""
    response = await client.put("/persona/agent", json={"text": "x" * 20_001})

    assert response.status_code == 422
