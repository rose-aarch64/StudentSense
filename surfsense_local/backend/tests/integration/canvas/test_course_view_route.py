import pytest
from httpx import AsyncClient
from sqlalchemy import Engine, text

from shared.db import create_session_factory
from tests.integration.canvas import test_sync_linked_files as linked_files
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData
from tests.integration.canvas.test_sync_content import documents, folders, start, sync
from tests.integration.canvas.test_sync_outline import LINK, set_up

pytestmark = pytest.mark.integration


async def course_of(client: AsyncClient, ws: int) -> dict:
    """The Modules view's data for a workspace."""
    shown = await client.get(f"/canvas/workspaces/{ws}/course")
    assert shown.status_code == 200, shown.text
    return shown.json()


async def test_a_synced_class_returns_its_modules_in_order_with_document_ids(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Pages, files and labs become rows to tick; headers stay in their place."""
    ws = await set_up(client, canvas_site)

    shown = await course_of(client, ws)

    assert shown["synced"] is True
    (module,) = shown["modules"]
    assert module["name"] == "Module A"
    assert module["folder_id"] == (await folders(client, ws))["01 · Module A"]
    assert [i["title"] for i in module["items"]] == [
        "LEARN",
        "Intro",
        "Deck.pdf",
        "APPLY",
        "Lab 1",
        "Blog",
    ]
    held = await documents(client, ws)
    by_title = {i["title"]: i for i in module["items"]}
    assert by_title["Intro"]["document_id"] == held["Canvas · Page · Intro"]["id"]
    assert by_title["Deck.pdf"]["document_id"] == held["Deck.pdf"]["id"]
    assert by_title["Lab 1"]["document_id"] == held["Canvas · Assignment · Lab 1"]["id"]
    assert by_title["Lab 1"]["points"] == 100.0
    assert by_title["LEARN"]["document_id"] is None
    assert shown["textbook_folder_id"] == (await folders(client, ws))["Textbook"]
    assert shown["notes"]["assignments"] == held["Canvas · Assignments"]["id"]


async def test_the_file_map_holds_module_files_and_linked_files(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A link in a note finds its file by the Canvas id the link names."""
    await start(client, canvas_site)
    linked_files.set_up(canvas_site)
    ws = await sync(client)

    shown = await course_of(client, ws)

    held = await documents(client, ws)
    assert shown["files"] == {
        "55": held["Syllabus.pdf"]["id"],
        "56": held["Handout.pdf"]["id"],
        "57": held["Lab sheet.pdf"]["id"],
    }


async def test_the_file_map_holds_only_this_workspaces_files(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Another class's files are not this class's to open."""
    canvas_site.courses = [
        {"id": 1, "name": "Bio", "term": {"name": "2026/FA"}},
        {"id": 2, "name": "Art", "term": {"name": "2026/FA"}},
    ]
    one, two = canvas_site.course(1), canvas_site.course(2)
    one.files = {55: ("One.pdf", linked_files.PDF + b"55")}
    one.syllabus = '<a href="/courses/1/files/55">x</a>'
    # A class with no module has no outline, so no view.
    one.modules = [ModuleData(5, "Module A")]
    two.modules = [ModuleData(6, "Module B")]
    two.files = {70: ("Two.pdf", linked_files.PDF + b"70")}
    two.syllabus = '<a href="/courses/2/files/70">y</a>'
    connected = await client.put(
        "/canvas/connection", json={"base_url": canvas_site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text
    synced = await client.post("/canvas/sync", json={})
    assert synced.status_code == 200, synced.text
    spaces = {c["canvas_id"]: c["workspace_id"] for c in synced.json()["courses"]}

    first = await course_of(client, spaces[1])
    second = await course_of(client, spaces[2])

    assert list(first["files"]) == ["55"]
    assert list(second["files"]) == ["70"]


async def test_a_link_item_has_a_url_and_no_document(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A link is followed, not ticked."""
    ws = await set_up(client, canvas_site)

    items = (await course_of(client, ws))["modules"][0]["items"]

    blog = next(i for i in items if i["title"] == "Blog")
    assert blog["url"] == LINK
    assert blog["document_id"] is None


async def test_a_graded_quiz_row_is_tied_to_its_assignment_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The module lists the quiz by its quiz id; the note is the assignment's."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [
        {
            "id": 7,
            "name": "Quiz 1",
            "quiz_id": 40,
            "due_at": None,
            "points_possible": 10.0,
            "submission": {"workflow_state": "unsubmitted"},
        }
    ]
    data.modules = [
        ModuleData(
            5,
            "Module A",
            items=[{"type": "Quiz", "title": "Quiz 1", "content_id": 40}],
        )
    ]
    ws = await sync(client)

    (item,) = (await course_of(client, ws))["modules"][0]["items"]

    held = await documents(client, ws)
    assert item["document_id"] == held["Canvas · Assignment · Quiz 1"]["id"]


async def test_a_module_of_only_subheaders_has_no_folder_id(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Nothing was filed for it, so its header has nothing to tick."""
    course = await start(client, canvas_site)
    canvas_site.course(course).modules = [
        ModuleData(6, "Policy", items=[{"type": "SubHeader", "title": "No Device"}])
    ]

    ws = await sync(client)

    (module,) = (await course_of(client, ws))["modules"]
    assert module["folder_id"] is None


async def test_a_workspace_with_no_canvas_course_is_not_synced(
    client: AsyncClient,
) -> None:
    """The Modules view is offered only to a class Canvas made."""
    made = await client.post("/workspaces", json={"name": "Research"})

    shown = await course_of(client, made.json()["id"])

    assert shown["synced"] is False
    assert shown["needs_sync"] is False
    assert shown["modules"] == []


async def test_a_class_synced_before_outlines_existed_needs_a_sync(
    client: AsyncClient, canvas_site: CanvasSite, engine: Engine
) -> None:
    """The view tells the student to sync once instead of showing an empty page."""
    ws = await set_up(client, canvas_site)
    with create_session_factory(engine)() as session:
        session.execute(
            text(
                "UPDATE documents SET document_metadata = NULL "
                "WHERE title = 'Canvas · Modules'"
            )
        )
        session.commit()

    shown = await course_of(client, ws)

    assert shown["synced"] is False
    assert shown["needs_sync"] is True
    assert shown["modules"] == []
