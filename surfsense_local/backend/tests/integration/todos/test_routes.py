import pytest
from httpx import AsyncClient
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from modules.todos.models import Todo, TodoSource
from shared.db import create_session_factory

pytestmark = pytest.mark.integration


async def make_workspace(client: AsyncClient, name: str = "Bio") -> int:
    """Open a workspace and return its id."""
    response = await client.post("/workspaces", json={"name": name})
    return response.json()["id"]


async def test_a_created_task_is_listed(client: AsyncClient) -> None:
    """The first thing the list does: show what was just added."""
    created = await client.post(
        "/todos", json={"title": "Read ch. 4", "due_at": "2026-12-01T05:00:00Z"}
    )

    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Read ch. 4"
    assert task["done"] is False
    assert task["done_at"] is None
    assert task["source"] == "manual"
    assert task["due_at"].startswith("2026-12-01T05:00:00")

    listed = await client.get("/todos")

    assert [t["id"] for t in listed.json()] == [task["id"]]


async def test_open_tasks_list_soonest_due_first_then_undated_then_done(
    client: AsyncClient,
) -> None:
    """A list that buries what is due tomorrow under what is done is no use."""
    await client.post("/todos", json={"title": "undated"})
    later = {"title": "later", "due_at": "2026-12-09T00:00:00Z"}
    sooner = {"title": "sooner", "due_at": "2026-12-01T00:00:00Z"}
    old = {"title": "finished", "due_at": "2026-11-01T00:00:00Z"}
    await client.post("/todos", json=later)
    await client.post("/todos", json=sooner)
    finished = await client.post("/todos", json=old)
    await client.patch(f"/todos/{finished.json()['id']}", json={"done": True})

    listed = await client.get("/todos")

    titles = [t["title"] for t in listed.json()]
    assert titles == ["sooner", "later", "undated", "finished"]


async def test_a_task_can_be_checked_and_unchecked(client: AsyncClient) -> None:
    """Checking stamps when; unchecking clears it, so a mistake is undoable."""
    task = (await client.post("/todos", json={"title": "Lab 1"})).json()

    checked = await client.patch(f"/todos/{task['id']}", json={"done": True})

    assert checked.json()["done"] is True
    assert checked.json()["done_at"] is not None

    unchecked = await client.patch(f"/todos/{task['id']}", json={"done": False})

    assert unchecked.json()["done"] is False
    assert unchecked.json()["done_at"] is None


async def test_an_edit_changes_only_the_fields_it_names(client: AsyncClient) -> None:
    """Renaming a task must not wipe its date; only an explicit null does."""
    due = "2026-12-01T00:00:00Z"
    created = await client.post("/todos", json={"title": "Lab 1", "due_at": due})
    task = created.json()

    renamed = await client.patch(f"/todos/{task['id']}", json={"title": "Lab 2"})

    assert renamed.json()["title"] == "Lab 2"
    assert renamed.json()["due_at"] == task["due_at"]

    cleared = await client.patch(f"/todos/{task['id']}", json={"due_at": None})

    assert cleared.json()["due_at"] is None


async def test_the_list_narrows_to_a_workspace_and_to_open_tasks(
    client: AsyncClient,
) -> None:
    """One class's list, and what is still to do in it."""
    bio = await make_workspace(client, "Bio")
    chem = await make_workspace(client, "Chem")
    await client.post("/todos", json={"title": "bio open", "workspace_id": bio})
    done = await client.post("/todos", json={"title": "bio done", "workspace_id": bio})
    await client.patch(f"/todos/{done.json()['id']}", json={"done": True})
    await client.post("/todos", json={"title": "chem open", "workspace_id": chem})

    in_bio = await client.get("/todos", params={"workspace_id": bio})
    open_in_bio = await client.get(
        "/todos", params={"workspace_id": bio, "done": "false"}
    )

    assert {t["title"] for t in in_bio.json()} == {"bio open", "bio done"}
    assert [t["title"] for t in open_in_bio.json()] == ["bio open"]


async def test_a_task_in_a_missing_workspace_is_refused(client: AsyncClient) -> None:
    """A task for a workspace that does not exist would be orphaned at birth."""
    response = await client.post("/todos", json={"title": "x", "workspace_id": 999})

    assert response.status_code == 404


async def test_a_blank_title_is_rejected(client: AsyncClient) -> None:
    """A task of spaces would render as an empty row."""
    response = await client.post("/todos", json={"title": "   "})

    assert response.status_code == 422


async def test_a_deleted_task_is_gone(client: AsyncClient) -> None:
    """Delete is final, and a second delete says so."""
    task = (await client.post("/todos", json={"title": "x"})).json()

    assert (await client.delete(f"/todos/{task['id']}")).status_code == 204
    assert (await client.delete(f"/todos/{task['id']}")).status_code == 404
    assert (await client.get("/todos")).json() == []


async def test_deleting_a_workspace_deletes_its_tasks(client: AsyncClient) -> None:
    """Tasks go with their workspace, as its documents do; a loose task stays."""
    bio = await make_workspace(client)
    await client.post("/todos", json={"title": "bio task", "workspace_id": bio})
    await client.post("/todos", json={"title": "no workspace"})

    await client.delete(f"/workspaces/{bio}")

    remaining = (await client.get("/todos")).json()
    assert [t["title"] for t in remaining] == ["no workspace"]


def test_one_source_key_names_one_task(engine: Engine) -> None:
    """The Canvas sync finds its task again by this key, so it cannot repeat."""
    factory = create_session_factory(engine)
    with factory() as session:
        first = Todo(title="a", source=TodoSource.CANVAS, source_key="assignment:1")
        session.add(first)
        session.commit()
        twin = Todo(title="b", source=TodoSource.CANVAS, source_key="assignment:1")
        session.add(twin)
        with pytest.raises(IntegrityError):
            session.commit()


def test_manual_tasks_carry_no_key_and_may_repeat(engine: Engine) -> None:
    """Two manual tasks may share a title; a NULL key never collides."""
    factory = create_session_factory(engine)
    with factory() as session:
        session.add_all([Todo(title="a"), Todo(title="a")])
        session.commit()
