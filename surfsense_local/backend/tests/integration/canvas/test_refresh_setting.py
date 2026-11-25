import pytest
from httpx import AsyncClient
from sqlalchemy import Engine, text

from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite

pytestmark = pytest.mark.integration


async def connect(client: AsyncClient, site: CanvasSite) -> None:
    """Connect the stand-in school with its good token."""
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text


async def status_of(client: AsyncClient) -> dict:
    """The connection as the API shows it."""
    return (await client.get("/canvas/connection")).json()


async def test_a_new_connection_has_the_refresh_off(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The refresh uses the token on its own, so it waits to be asked for."""
    await connect(client, canvas_site)

    status = await status_of(client)

    assert status["auto_refresh"] is False
    assert status["refreshed_at"] is None
    assert status["refresh_error"] is None


async def test_the_refresh_can_be_turned_on_and_read_back(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The switch in Settings reads back what it set."""
    await connect(client, canvas_site)

    turned_on = await client.patch("/canvas/connection", json={"auto_refresh": True})

    assert turned_on.status_code == 200, turned_on.text
    assert turned_on.json()["auto_refresh"] is True
    assert (await status_of(client))["auto_refresh"] is True


async def test_the_setting_needs_a_connection(client: AsyncClient) -> None:
    """There is no token to refresh with until Canvas is connected."""
    refused = await client.patch("/canvas/connection", json={"auto_refresh": True})

    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "canvas_not_connected"


async def test_the_setting_takes_only_auto_refresh(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Nothing but the switch can be changed here."""
    await connect(client, canvas_site)

    assert (await client.patch("/canvas/connection", json={})).status_code == 422
    extra = await client.patch(
        "/canvas/connection", json={"auto_refresh": True, "x": 1}
    )
    assert extra.status_code == 422


async def test_disconnecting_forgets_the_setting(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A school connected again later starts with the refresh off."""
    await connect(client, canvas_site)
    await client.patch("/canvas/connection", json={"auto_refresh": True})

    await client.delete("/canvas/connection")
    await connect(client, canvas_site)

    assert (await status_of(client))["auto_refresh"] is False


async def test_reconnecting_with_a_new_token_keeps_the_setting_and_clears_the_error(
    client: AsyncClient, canvas_site: CanvasSite, engine: Engine
) -> None:
    """A new token may be the fix for a refused one; it is no reason to switch off."""
    await connect(client, canvas_site)
    await client.patch("/canvas/connection", json={"auto_refresh": True})
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE canvas_connection SET refresh_error = 'canvas_token_refused'")
        )

    await connect(client, canvas_site)

    status = await status_of(client)
    assert status["auto_refresh"] is True
    assert status["refresh_error"] is None
