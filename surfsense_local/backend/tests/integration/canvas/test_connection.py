import pytest
from httpx import AsyncClient
from sqlalchemy import Engine, text

from shared.db import create_session_factory
from shared.secrets import decrypt
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite

pytestmark = pytest.mark.integration


async def test_there_is_no_connection_at_first(client: AsyncClient) -> None:
    """A fresh install has no school to read."""
    status = await client.get("/canvas/connection")

    assert status.status_code == 200
    assert status.json() == {
        "connected": False,
        "base_url": None,
        "user_name": None,
        "auto_refresh": False,
        "refreshed_at": None,
        "refresh_error": None,
    }


async def test_connecting_checks_the_token_with_canvas_and_names_the_user(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A token that cannot read Canvas is found out now, not at the first sync."""
    connected = await client.put(
        "/canvas/connection", json={"base_url": canvas_site.base, "token": GOOD_TOKEN}
    )

    assert connected.status_code == 200, connected.text
    expected = {
        "connected": True,
        "base_url": canvas_site.base,
        "user_name": "Rose B",
        "auto_refresh": False,
        "refreshed_at": None,
        "refresh_error": None,
    }
    assert connected.json() == expected
    assert canvas_site.asked[0].headers["authorization"] == f"Bearer {GOOD_TOKEN}"
    assert (await client.get("/canvas/connection")).json() == expected
    assert GOOD_TOKEN not in connected.text


async def test_the_token_is_kept_encrypted(
    client: AsyncClient, canvas_site: CanvasSite, engine: Engine
) -> None:
    """Whoever reads the database file learns no one's Canvas access."""
    await client.put(
        "/canvas/connection", json={"base_url": canvas_site.base, "token": GOOD_TOKEN}
    )

    with create_session_factory(engine)() as session:
        stored = session.execute(
            text("SELECT token_ciphertext FROM canvas_connection")
        ).scalar_one()

    assert GOOD_TOKEN.encode() not in stored
    assert decrypt(stored) == GOOD_TOKEN


async def test_a_refused_token_is_not_stored(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas said no, so there is nothing to connect."""
    refused = await client.put(
        "/canvas/connection", json={"base_url": canvas_site.base, "token": "wrong"}
    )

    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "canvas_token_refused"
    assert (await client.get("/canvas/connection")).json()["connected"] is False


async def test_a_school_not_yet_allowed_is_asked_about_before_anything_is_sent(
    client: AsyncClient,
) -> None:
    """Nothing leaves the machine until its host is allowed, as everywhere else."""
    refused = await client.put(
        "/canvas/connection",
        json={"base_url": "https://school.example", "token": GOOD_TOKEN},
    )

    assert refused.status_code == 403
    detail = refused.json()["detail"]
    assert detail["code"] == "egress_disabled"
    assert detail["hosts"] == ["school.example"]
    assert detail["purpose"] == "canvas"
    assert (await client.get("/canvas/connection")).json()["connected"] is False


async def test_a_bare_host_name_is_taken_as_https(client: AsyncClient) -> None:
    """People type the address they know: the school's host, with no scheme."""
    refused = await client.put(
        "/canvas/connection", json={"base_url": "school.example", "token": GOOD_TOKEN}
    )

    assert refused.status_code == 403
    assert refused.json()["detail"]["hosts"] == ["school.example"]


async def test_plain_http_is_refused_off_this_computer(client: AsyncClient) -> None:
    """The token would cross the network in the clear."""
    refused = await client.put(
        "/canvas/connection",
        json={"base_url": "http://school.example", "token": GOOD_TOKEN},
    )

    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "canvas_needs_https"


async def test_only_the_address_is_kept_not_a_path_after_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A pasted link to a course page still means the school."""
    connected = await client.put(
        "/canvas/connection",
        json={"base_url": f"{canvas_site.base}/courses/7/", "token": GOOD_TOKEN},
    )

    assert connected.json()["base_url"] == canvas_site.base


async def test_the_connection_can_be_removed(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Disconnecting forgets the token."""
    await client.put(
        "/canvas/connection", json={"base_url": canvas_site.base, "token": GOOD_TOKEN}
    )

    removed = await client.delete("/canvas/connection")

    assert removed.status_code == 204
    assert (await client.get("/canvas/connection")).json()["connected"] is False
    assert (await client.delete("/canvas/connection")).status_code == 204
