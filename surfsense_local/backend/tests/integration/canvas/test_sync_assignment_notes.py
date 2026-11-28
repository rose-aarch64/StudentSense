import pytest
from httpx import AsyncClient

from tests.integration.canvas.conftest import CanvasSite, ModuleData
from tests.integration.canvas.test_sync_content import (
    content_of,
    documents,
    folders,
    start,
    sync,
)

pytestmark = pytest.mark.integration


def lab(
    assignment_id: int,
    name: str,
    description: str | None = "<p>Use <b>nmap</b> on the lab host</p>",
) -> dict:
    """An assignment as Canvas lists it, with its description and points."""
    return {
        "id": assignment_id,
        "name": name,
        "description": description,
        "due_at": "2026-09-08T04:00:00Z",
        "points_possible": 100.0,
        "submission": {"workflow_state": "unsubmitted"},
    }


async def notes_of(client: AsyncClient, ws: int) -> dict[str, dict]:
    """The workspace's assignment notes by title."""
    found = await documents(client, ws)
    return {t: d for t, d in found.items() if t.startswith("Canvas · Assignment ·")}


async def test_an_assignment_is_a_note_in_its_modules_folder(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A lab can then be ticked as a source and found by search."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [lab(7, "Lab 1")]
    data.modules = [ModuleData(5, "Module A", assignments=[7])]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Assignment · Lab 1"]
    assert note["folder_id"] == (await folders(client, ws))["01 · Module A"]
    text = await content_of(client, ws, note["id"])
    assert "Use nmap on the lab host" in text and "<" not in text
    assert "2026-09-08" in text and "100" in text


async def test_a_link_in_an_assignment_keeps_its_address(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The lab's instructions point at a page; the note must still point there."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [
        lab(7, "Lab 1", '<p>Read <a href="https://example.org/guide">the guide</a></p>')
    ]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Assignment · Lab 1"]
    text = await content_of(client, ws, note["id"])
    assert "[the guide](https://example.org/guide)" in text


async def test_an_assignment_in_no_module_goes_to_unsorted(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas lists it, but no module holds it, so no module folder fits."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [lab(7, "Lab 1")]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Assignment · Lab 1"]
    assert note["folder_id"] == (await folders(client, ws))["Unsorted"]


async def test_an_assignment_with_no_description_still_makes_a_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The due date and points are worth having even with nothing to read."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [lab(7, "Exam", description=None)]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Assignment · Exam"]
    assert "100" in await content_of(client, ws, note["id"])


async def test_two_assignments_with_one_title_get_distinct_notes(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas allows two assignments with one name; neither may overwrite the other."""
    course = await start(client, canvas_site)
    canvas_site.course(course).assignments = [lab(7, "Quiz"), lab(8, "Quiz")]

    ws = await sync(client)

    assert len(await notes_of(client, ws)) == 2


async def test_a_graded_quiz_is_filed_in_the_module_that_holds_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas lists a graded quiz among assignments but names it by its quiz id in a module."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [{**lab(7, "Quiz 1"), "quiz_id": 40}]
    data.modules = [
        ModuleData(
            5,
            "Module A",
            items=[{"type": "Quiz", "title": "Quiz 1", "content_id": 40}],
        )
    ]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Assignment · Quiz 1"]
    assert note["folder_id"] == (await folders(client, ws))["01 · Module A"]


async def test_a_graded_discussion_is_filed_in_the_module_that_holds_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The same, for a discussion named by its topic id."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [{**lab(7, "Talk"), "discussion_topic": {"id": 60}}]
    data.modules = [
        ModuleData(
            5,
            "Module A",
            items=[{"type": "Discussion", "title": "Talk", "content_id": 60}],
        )
    ]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Assignment · Talk"]
    assert note["folder_id"] == (await folders(client, ws))["01 · Module A"]


async def test_renaming_an_assignment_in_canvas_retitles_its_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The note is found again by Canvas's id, so no second one appears."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.assignments = [lab(7, "Lab 1")]
    ws = await sync(client)
    first = (await notes_of(client, ws))["Canvas · Assignment · Lab 1"]["id"]

    data.assignments = [lab(7, "Lab 1 (revised)")]
    await sync(client)

    found = await notes_of(client, ws)
    assert list(found) == ["Canvas · Assignment · Lab 1 (revised)"]
    assert found["Canvas · Assignment · Lab 1 (revised)"]["id"] == first
