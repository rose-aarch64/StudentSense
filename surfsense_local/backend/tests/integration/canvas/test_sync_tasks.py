import pytest
from httpx import AsyncClient

from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite

pytestmark = pytest.mark.integration


def assignment(
    assignment_id: int,
    name: str,
    due: str | None = "2026-12-01T05:00:00Z",
    state: str = "unsubmitted",
) -> dict:
    """An assignment as Canvas lists it, with the student's own submission."""
    return {
        "id": assignment_id,
        "name": name,
        "due_at": due,
        "submission": {"workflow_state": state},
    }


async def start(client: AsyncClient, site: CanvasSite) -> int:
    """Connect the stand-in school, which has one course, and return its Canvas id."""
    site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text
    return 1


async def sync(client: AsyncClient) -> int:
    """Sync, and return the course's workspace id."""
    synced = await client.post("/canvas/sync", json={})
    assert synced.status_code == 200, synced.text
    return synced.json()["courses"][0]["workspace_id"]


async def tasks(client: AsyncClient, workspace_id: int) -> dict[str, dict]:
    """The workspace's tasks by title."""
    listed = await client.get("/todos", params={"workspace_id": workspace_id})
    return {t["title"]: t for t in listed.json()}


async def test_an_assignment_becomes_a_task_in_its_class_with_its_due_date(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """What is due, in the to-do list, beside the student's own tasks."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [assignment(31, "Lab 1")]

    ws = await sync(client)

    task = (await tasks(client, ws))["Lab 1"]
    assert task["source"] == "canvas"
    assert task["due_at"].startswith("2026-12-01T05:00:00")
    assert task["done"] is False


async def test_an_assignment_with_no_due_date_is_still_a_task(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Undated work is still work."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [assignment(32, "Reading", due=None)]

    ws = await sync(client)

    assert (await tasks(client, ws))["Reading"]["due_at"] is None


async def test_a_second_sync_updates_the_task_it_made_and_adds_none(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """An instructor moving a deadline moves it here too."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [assignment(31, "Lab 1")]
    ws = await sync(client)
    first = (await tasks(client, ws))["Lab 1"]

    data.assignments = [assignment(31, "Lab 1 (revised)", due="2026-12-08T05:00:00Z")]
    await sync(client)

    after = await tasks(client, ws)
    assert list(after) == ["Lab 1 (revised)"]
    assert after["Lab 1 (revised)"]["id"] == first["id"]
    assert after["Lab 1 (revised)"]["due_at"].startswith("2026-12-08")


async def test_a_submitted_assignment_is_marked_done(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Handing it in is doing it."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [assignment(31, "Lab 1")]
    ws = await sync(client)

    data.assignments = [assignment(31, "Lab 1", state="submitted")]
    await sync(client)

    assert (await tasks(client, ws))["Lab 1"]["done"] is True


async def test_a_task_the_user_checked_stays_checked(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas may mark a task done; it never takes a student's check away."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [assignment(31, "Lab 1")]
    ws = await sync(client)
    task = (await tasks(client, ws))["Lab 1"]
    await client.patch(f"/todos/{task['id']}", json={"done": True})

    await sync(client)

    assert (await tasks(client, ws))["Lab 1"]["done"] is True


async def test_a_task_the_user_deleted_is_not_made_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Deleting a task is a choice; the next sync respects it."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [assignment(31, "Lab 1")]
    ws = await sync(client)
    task = (await tasks(client, ws))["Lab 1"]
    await client.delete(f"/todos/{task['id']}")

    await sync(client)

    assert await tasks(client, ws) == {}


async def test_a_workspace_made_fresh_brings_its_tasks_back_with_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Its tasks went with the workspace; that was not a choice to drop them."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [assignment(31, "Lab 1")]
    first = await sync(client)
    await client.delete(f"/workspaces/{first}")

    second = await sync(client)

    assert "Lab 1" in await tasks(client, second)


async def test_an_assignment_removed_from_canvas_leaves_its_task_alone(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Nothing the sync made is deleted for Canvas having dropped it."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [assignment(31, "Lab 1")]
    ws = await sync(client)

    data.assignments = []
    await sync(client)

    assert "Lab 1" in await tasks(client, ws)
