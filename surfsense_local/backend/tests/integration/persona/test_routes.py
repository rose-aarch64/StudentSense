import pytest
from httpx import AsyncClient

from modules.persona.store import persona_text

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
