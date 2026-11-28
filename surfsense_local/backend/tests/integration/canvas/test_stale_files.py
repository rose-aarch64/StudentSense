import pytest
from httpx import AsyncClient

from shared.queue import ingest_queue
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData

pytestmark = pytest.mark.integration

OLD = b"%PDF-1.4\n%the first version\n"
NEW = b"%PDF-1.4\n%the teacher's second version, longer\n"


async def start(client: AsyncClient, site: CanvasSite) -> int:
    """Connect the stand-in school, whose one course holds one file, and sync it."""
    site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text
    data = site.course(1)
    data.files = {55: ("Week1.pdf", OLD)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    return 1


async def sync(client: AsyncClient) -> dict:
    """Sync, and return the course's entry in the answer."""
    synced = await client.post("/canvas/sync", json={})
    assert synced.status_code == 200, synced.text
    return synced.json()["courses"][0]


async def stale(client: AsyncClient) -> dict:
    """What the read-only check says about the first course."""
    checked = await client.get("/canvas/stale")
    assert checked.status_code == 200, checked.text
    return checked.json()["courses"][0]


async def document(client: AsyncClient, workspace_id: int, title: str) -> dict:
    """One of the workspace's documents, by title."""
    listed = await client.get(f"/workspaces/{workspace_id}/documents?limit=200")
    return {d["title"]: d for d in listed.json()}[title]


def downloads(site: CanvasSite) -> list[str]:
    """The signed links that were fetched."""
    return [r.url.path for r in site.asked if r.url.path.startswith("/download/")]


async def test_a_file_the_text_links_to_is_not_reported_gone_by_the_check(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The check reads module files only; a linked file is not one it can miss."""
    await start(client, canvas_site)
    data = canvas_site.course(1)
    data.files[56] = ("Handout.pdf", NEW)
    data.syllabus = '<a href="/courses/1/files/56">handout</a>'
    synced = await sync(client)
    assert (await document(client, synced["workspace_id"], "Handout.pdf"))["id"]

    checked = await stale(client)

    assert checked["gone"] == []


async def test_a_file_that_has_not_changed_is_not_stale(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The check says so, and says nothing else."""
    await start(client, canvas_site)
    await sync(client)

    checked = await stale(client)

    assert checked["changed"] == [] and checked["gone"] == []


async def test_a_file_edited_in_canvas_is_reported_changed_without_fetching_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Checking is cheap: Canvas is asked about the file, never for its bytes."""
    await start(client, canvas_site)
    await sync(client)
    canvas_site.course(1).edit_file(55, NEW, "2026-11-20T00:00:00Z")

    checked = await stale(client)

    assert checked["changed"] == ["Week1.pdf"]
    assert downloads(canvas_site) == ["/download/55"]  # only the first sync's


async def test_a_file_removed_from_canvas_is_reported_gone_and_left_in_place(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The student may still want it; only they decide."""
    await start(client, canvas_site)
    course = await sync(client)
    data = canvas_site.course(1)
    data.modules[0].files = []

    checked = await stale(client)

    assert checked["gone"] == ["Week1.pdf"]
    assert (await document(client, course["workspace_id"], "Week1.pdf"))["id"]


async def test_the_check_changes_nothing(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A question is not an order: no document is touched and nothing is queued."""
    await start(client, canvas_site)
    course = await sync(client)
    before = await document(client, course["workspace_id"], "Week1.pdf")
    canvas_site.course(1).edit_file(55, NEW, "2026-11-20T00:00:00Z")
    queued = len(ingest_queue.pending())

    await stale(client)

    after = await document(client, course["workspace_id"], "Week1.pdf")
    assert after == before
    assert len(ingest_queue.pending()) == queued


async def test_a_sync_fetches_an_edited_file_again_and_keeps_its_document(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Same document, new bytes, read again, so search stops answering from the old copy."""
    await start(client, canvas_site)
    first = await sync(client)
    before = await document(client, first["workspace_id"], "Week1.pdf")
    canvas_site.course(1).edit_file(55, NEW, "2026-11-20T00:00:00Z")
    queued = len(ingest_queue.pending())

    refreshed = await sync(client)

    after = await document(client, refreshed["workspace_id"], "Week1.pdf")
    assert after["id"] == before["id"]
    assert after["status"] == "pending"
    assert refreshed["refreshed"] == ["Week1.pdf"]
    assert downloads(canvas_site) == ["/download/55", "/download/55"]
    assert len(ingest_queue.pending()) == queued + 1
    assert (await stale(client))["changed"] == []


async def test_a_second_sync_after_the_refresh_fetches_nothing(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Once current, a file is left alone again."""
    await start(client, canvas_site)
    await sync(client)
    canvas_site.course(1).edit_file(55, NEW, "2026-11-20T00:00:00Z")
    await sync(client)

    again = await sync(client)

    assert again["refreshed"] == []
    assert len(downloads(canvas_site)) == 2


async def test_a_sync_reports_a_removed_file_and_leaves_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Gone from Canvas is told, not acted on."""
    await start(client, canvas_site)
    first = await sync(client)
    canvas_site.course(1).modules[0].files = []

    again = await sync(client)

    assert again["gone"] == ["Week1.pdf"]
    assert (await document(client, first["workspace_id"], "Week1.pdf"))["id"]


async def test_an_edit_that_cannot_be_read_keeps_the_old_copy(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A broken re-upload must not replace a good file."""
    await start(client, canvas_site)
    first = await sync(client)
    before = await document(client, first["workspace_id"], "Week1.pdf")
    canvas_site.course(1).edit_file(55, b"not a pdf at all", "2026-11-20T00:00:00Z")

    refreshed = await sync(client)

    assert refreshed["refreshed"] == []
    after = await document(client, refreshed["workspace_id"], "Week1.pdf")
    assert after["id"] == before["id"] and after["status"] == before["status"]
