import pytest
from httpx import AsyncClient

from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite

pytestmark = pytest.mark.integration


def course(course_id: int, name: str, term: str = "2026/FA") -> dict:
    """A course as Canvas lists it."""
    return {"id": course_id, "name": name, "term": {"name": term}}


async def connect(client: AsyncClient, site: CanvasSite) -> None:
    """Connect the stand-in school with its good token."""
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text


async def workspace_names(client: AsyncClient) -> list[str]:
    """The names of the workspaces, oldest first."""
    return [w["name"] for w in (await client.get("/workspaces")).json()]


async def test_a_sync_needs_a_connection_first(client: AsyncClient) -> None:
    """There is no school to read until one is connected."""
    refused = await client.post("/canvas/sync", json={})

    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "canvas_not_connected"


async def test_a_sync_is_refused_until_an_embedding_model_is_chosen(
    unlocked_client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Notes and files queued now would have no model to be read with."""
    canvas_site.courses = [course(1, "Network Security")]
    await connect(unlocked_client, canvas_site)

    refused = await unlocked_client.post("/canvas/sync", json={})

    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "embedding_not_chosen"
    assert "Network Security" not in await workspace_names(unlocked_client)


async def test_each_active_course_becomes_a_workspace_named_after_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """One workspace per class, so each class has its own sources and chat."""
    canvas_site.courses = [course(1, "Network Security"), course(2, "Photography")]
    await connect(client, canvas_site)
    before = await workspace_names(client)

    synced = await client.post("/canvas/sync", json={})

    assert synced.status_code == 200, synced.text
    assert [c["name"] for c in synced.json()["courses"]] == [
        "Network Security",
        "Photography",
    ]
    assert await workspace_names(client) == [
        *before,
        "Network Security",
        "Photography",
    ]


async def test_a_second_sync_finds_its_workspaces_instead_of_making_more(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Syncing is safe to repeat."""
    canvas_site.courses = [course(1, "Network Security")]
    await connect(client, canvas_site)
    first = (await client.post("/canvas/sync", json={})).json()
    count = len(await workspace_names(client))

    second = (await client.post("/canvas/sync", json={})).json()

    assert second["courses"][0]["workspace_id"] == first["courses"][0]["workspace_id"]
    assert len(await workspace_names(client)) == count


async def test_a_renamed_course_renames_its_workspace(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The link is the course's id, so a new name is the same class."""
    canvas_site.courses = [course(1, "Network Security")]
    await connect(client, canvas_site)
    await client.post("/canvas/sync", json={})

    canvas_site.courses = [course(1, "Network Security II")]
    await client.post("/canvas/sync", json={})

    names = await workspace_names(client)
    assert "Network Security II" in names
    assert "Network Security" not in names


async def test_a_workspace_with_the_course_s_exact_name_is_adopted_once(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Classes set up by hand or by an earlier tool are not duplicated."""
    made = await client.post("/workspaces", json={"name": "Photography"})
    canvas_site.courses = [course(2, "Photography")]
    await connect(client, canvas_site)

    synced = (await client.post("/canvas/sync", json={})).json()

    assert synced["courses"][0]["workspace_id"] == made.json()["id"]
    assert (await workspace_names(client)).count("Photography") == 1


async def test_a_workspace_the_user_deleted_comes_back_on_the_next_sync(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Deleting a class's workspace is not a standing order to hide the class."""
    canvas_site.courses = [course(1, "Network Security")]
    await connect(client, canvas_site)
    first = (await client.post("/canvas/sync", json={})).json()
    await client.delete(f"/workspaces/{first['courses'][0]['workspace_id']}")
    assert "Network Security" not in await workspace_names(client)

    second = (await client.post("/canvas/sync", json={})).json()

    assert "Network Security" in await workspace_names(client)
    returned = await client.get(f"/workspaces/{second['courses'][0]['workspace_id']}")
    assert returned.status_code == 200


async def test_a_term_filter_leaves_other_terms_alone(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """An old orientation course need not get a workspace."""
    canvas_site.courses = [
        course(1, "Network Security"),
        course(9, "Welcome to BC", term="Default Term"),
    ]
    await connect(client, canvas_site)

    synced = await client.post("/canvas/sync", json={"term": "2026/FA"})

    assert [c["name"] for c in synced.json()["courses"]] == ["Network Security"]
    assert "Welcome to BC" not in await workspace_names(client)


async def test_a_sync_with_no_term_named_brings_in_only_the_current_term(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The orientation course sits in a term with no dates, so it stays out."""
    current = course(1, "Network Security")
    current["term"] |= {
        "start_at": "2000-01-01T00:00:00Z",
        "end_at": "2999-01-01T00:00:00Z",
    }
    canvas_site.courses = [current, course(9, "Welcome to BC", term="Default Term")]
    await connect(client, canvas_site)

    synced = await client.post("/canvas/sync", json={})

    assert [c["name"] for c in synced.json()["courses"]] == ["Network Security"]
    assert "Welcome to BC" not in await workspace_names(client)
