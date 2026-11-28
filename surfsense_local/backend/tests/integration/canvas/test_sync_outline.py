import pytest
from httpx import AsyncClient

from shared.queue import ingest_queue
from tests.integration.canvas.conftest import CanvasSite, ModuleData
from tests.integration.canvas.test_sync_assignment_notes import lab
from tests.integration.canvas.test_sync_content import (
    documents,
    page,
    start,
    sync,
)

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n%a stand-in file\n"
LINK = "https://example.org/blog"


def mixed_module() -> ModuleData:
    """A module as a teacher builds one: headers between pages, files, labs and links."""
    return ModuleData(
        5,
        "Module A",
        items=[
            {"type": "SubHeader", "title": "LEARN"},
            {"type": "Page", "title": "Intro", "page_url": "intro"},
            {"type": "File", "title": "Deck.pdf", "content_id": 9},
            {"type": "SubHeader", "title": "APPLY"},
            {"type": "Assignment", "title": "Lab 1", "content_id": 7},
            {"type": "ExternalUrl", "title": "Blog", "external_url": LINK},
        ],
    )


async def outline_of(client: AsyncClient, ws: int) -> list[dict]:
    """The ordered modules the sync saved with the Modules note."""
    note = (await documents(client, ws))["Canvas · Modules"]
    detail = await client.get(f"/workspaces/{ws}/documents/{note['id']}")
    return detail.json()["document_metadata"]["canvas_modules"]


async def set_up(client: AsyncClient, site: CanvasSite) -> int:
    """Sync a class whose one module holds a page, a file, a lab and a link."""
    course = await start(client, site)
    data = site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.files = {9: ("Deck.pdf", PDF)}
    data.assignments = [lab(7, "Lab 1")]
    data.modules = [mixed_module()]
    return await sync(client)


async def test_the_modules_note_keeps_every_item_in_canvas_order(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The note's text lists items; the saved outline is what the Modules view draws."""
    ws = await set_up(client, canvas_site)

    (module,) = await outline_of(client, ws)

    assert module["name"] == "Module A"
    assert [(i["type"], i["title"]) for i in module["items"]] == [
        ("SubHeader", "LEARN"),
        ("Page", "Intro"),
        ("File", "Deck.pdf"),
        ("SubHeader", "APPLY"),
        ("Assignment", "Lab 1"),
        ("ExternalUrl", "Blog"),
    ]
    by_title = {i["title"]: i for i in module["items"]}
    assert by_title["Intro"]["canvas_id"] == 11
    assert by_title["Deck.pdf"]["canvas_id"] == 9
    assert by_title["Lab 1"]["canvas_id"] == 7
    assert by_title["Lab 1"]["points"] == 100.0
    assert by_title["Lab 1"]["due_at"].startswith("2026-09-08")
    assert by_title["Blog"]["url"] == LINK
    assert by_title["LEARN"]["canvas_id"] is None


async def test_editing_the_modules_note_keeps_the_outline(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A note edit changes its text only, so the view survives the user's edits."""
    ws = await set_up(client, canvas_site)
    note = (await documents(client, ws))["Canvas · Modules"]

    edited = await client.patch(
        f"/workspaces/{ws}/documents/{note['id']}", json={"content": "my own text"}
    )

    assert edited.status_code == 200, edited.text
    assert len(await outline_of(client, ws)) == 1


async def test_a_second_sync_with_nothing_new_does_not_read_the_modules_note_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Saving the outline alone must not queue work the worker would repeat."""
    ws = await set_up(client, canvas_site)
    note = (await documents(client, ws))["Canvas · Modules"]
    ingest_queue.flush()

    await sync(client)

    assert (note["id"],) not in [job.args for job in ingest_queue.pending()]


async def test_a_class_that_loses_every_module_shows_none(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """No Modules note is written for no modules, so the kept one must forget them."""
    ws = await set_up(client, canvas_site)
    (course,) = canvas_site.courses
    canvas_site.course(course["id"]).modules = []

    await sync(client)

    assert await outline_of(client, ws) == []
