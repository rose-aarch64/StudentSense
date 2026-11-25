import pytest
from httpx import AsyncClient

from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite

pytestmark = pytest.mark.integration

DATES = {"start_at": "2000-01-01T00:00:00Z", "end_at": "2999-01-01T00:00:00Z"}


def course(course_id: int, name: str, term: dict | None = None) -> dict:
    """A course in a current, dated term unless told otherwise."""
    term = term or {"id": 7, "name": "2026/FA", **DATES}
    return {"id": course_id, "name": name, "term": term}


async def connect(client: AsyncClient, site: CanvasSite) -> None:
    """Connect the stand-in school with its good token."""
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text


async def sync(client: AsyncClient) -> dict[str, int | None]:
    """Sync and return each course's workspace folder, by workspace name."""
    done = await client.post("/canvas/sync", json={})
    assert done.status_code == 200, done.text
    workspaces = (await client.get("/workspaces")).json()
    return {w["name"]: w["folder_id"] for w in workspaces}


async def folders(client: AsyncClient) -> dict[int, str]:
    """Every folder, as id to name."""
    return {f["id"]: f["name"] for f in (await client.get("/workspace-folders")).json()}


async def test_each_course_is_filed_in_a_folder_named_for_its_term(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """One folder per term keeps this term's classes together."""
    canvas_site.courses = [course(1, "Networks"), course(2, "Photography")]
    await connect(client, canvas_site)

    filed = await sync(client)

    names = await folders(client)
    assert list(names.values()) == ["2026/FA"]
    assert {filed["Networks"], filed["Photography"]} == set(names)


async def test_a_second_sync_reuses_the_folder(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The folder is found again by its Canvas term, not made twice."""
    canvas_site.courses = [course(1, "Networks")]
    await connect(client, canvas_site)
    await sync(client)

    await sync(client)

    assert list((await folders(client)).values()) == ["2026/FA"]


async def test_a_renamed_term_renames_its_folder(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The link is the term's id, so a new name is the same folder."""
    canvas_site.courses = [course(1, "Networks")]
    await connect(client, canvas_site)
    await sync(client)
    canvas_site.courses = [
        course(1, "Networks", {"id": 7, "name": "Fall 2026", **DATES})
    ]

    await sync(client)

    assert list((await folders(client)).values()) == ["Fall 2026"]


async def test_a_folder_with_the_terms_name_is_adopted_once(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A folder the user made already is used, not duplicated."""
    made = await client.post("/workspace-folders", json={"name": "2026/FA"})
    canvas_site.courses = [course(1, "Networks")]
    await connect(client, canvas_site)

    filed = await sync(client)

    assert list((await folders(client)).values()) == ["2026/FA"]
    assert filed["Networks"] == made.json()["id"]


async def test_a_workspace_the_user_moved_stays_where_they_put_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Sync files what has no folder, and never takes a workspace back."""
    canvas_site.courses = [course(1, "Networks")]
    await connect(client, canvas_site)
    await sync(client)
    mine = (await client.post("/workspace-folders", json={"name": "Mine"})).json()
    workspace = next(
        w for w in (await client.get("/workspaces")).json() if w["name"] == "Networks"
    )
    await client.patch(f"/workspaces/{workspace['id']}", json={"folder_id": mine["id"]})

    filed = await sync(client)

    assert filed["Networks"] == mine["id"]


async def test_a_workspace_already_synced_and_unfiled_is_filed_by_the_next_sync(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The classes from before folders existed move in on the next sync."""
    canvas_site.courses = [course(1, "Networks")]
    await connect(client, canvas_site)
    await sync(client)
    workspace = next(
        w for w in (await client.get("/workspaces")).json() if w["name"] == "Networks"
    )
    await client.patch(f"/workspaces/{workspace['id']}", json={"folder_id": None})

    filed = await sync(client)

    assert filed["Networks"] is not None


async def test_a_course_in_an_undated_term_is_left_unfiled(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """An orientation course in Default Term has no term worth a folder."""
    canvas_site.courses = [
        course(1, "Welcome", {"id": 1, "name": "Default Term"}),
    ]
    await connect(client, canvas_site)

    filed = await sync(client)

    assert filed["Welcome"] is None
    assert await folders(client) == {}


async def test_a_deleted_term_folder_is_made_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A link to a folder the user deleted is made good again."""
    canvas_site.courses = [course(1, "Networks")]
    await connect(client, canvas_site)
    await sync(client)
    (folder_id,) = await folders(client)
    await client.delete(f"/workspace-folders/{folder_id}")

    filed = await sync(client)

    assert filed["Networks"] is not None
    assert list((await folders(client)).values()) == ["2026/FA"]
