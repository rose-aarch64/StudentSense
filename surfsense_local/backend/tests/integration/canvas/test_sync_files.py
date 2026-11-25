import pytest
from httpx import AsyncClient

from shared.queue import ingest_queue
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n%a stand-in file\n"


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


async def documents(client: AsyncClient, workspace_id: int) -> dict[str, dict]:
    """The workspace's documents by title."""
    listed = await client.get(f"/workspaces/{workspace_id}/documents?limit=200")
    return {d["title"]: d for d in listed.json()}


async def folders(client: AsyncClient, workspace_id: int) -> dict[str, int]:
    """The workspace's folders by name, the Library's own left out."""
    listed = await client.get(f"/workspaces/{workspace_id}/folders")
    return {f["name"]: f["id"] for f in listed.json() if f["parent_id"] is not None}


def downloads(site: CanvasSite) -> list[str]:
    """The signed links the sync actually fetched."""
    return [r.url.path for r in site.asked if r.url.path.startswith("/download/")]


async def test_a_module_file_is_stored_in_its_module_folder_and_queued_to_be_read(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The file lands where Canvas keeps it, and becomes searchable."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]

    ws = await sync(client)

    stored = (await documents(client, ws))["Week1.pdf"]
    assert stored["document_type"] == "FILE"
    assert stored["folder_id"] == (await folders(client, ws))["01 · Module A"]
    assert (stored["id"],) in [job.args for job in ingest_queue.pending()]
    assert downloads(canvas_site) == ["/download/55"]


async def test_the_download_carries_no_canvas_token(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The signed link may be on another host, which must never see the token."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]

    await sync(client)

    fetched = [r for r in canvas_site.asked if r.url.path.startswith("/download/")]
    assert fetched and all("authorization" not in r.headers for r in fetched)


async def test_a_file_surfsense_cannot_read_is_never_downloaded(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """No point fetching what would only be refused."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {56: ("backup.zip", b"PK")}
    data.modules = [ModuleData(5, "Module A", files=[56])]

    ws = await sync(client)

    assert downloads(canvas_site) == []
    assert "backup.zip" not in await documents(client, ws)


async def test_a_second_sync_does_not_fetch_a_file_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Files are the heavy part; an unchanged one is left alone."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    ws = await sync(client)
    first = (await documents(client, ws))["Week1.pdf"]

    await sync(client)

    assert downloads(canvas_site) == ["/download/55"]
    assert (await documents(client, ws))["Week1.pdf"]["id"] == first["id"]


async def test_a_file_moved_to_another_module_moves_without_being_fetched_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Where it lives in Canvas is where it lives here."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [
        ModuleData(5, "Module A", files=[55]),
        ModuleData(6, "Module B"),
    ]
    ws = await sync(client)
    first = (await documents(client, ws))["Week1.pdf"]

    data.modules[0].files = []
    data.modules[1].files = [55]
    await sync(client)

    moved = (await documents(client, ws))["Week1.pdf"]
    assert moved["id"] == first["id"]
    assert moved["folder_id"] == (await folders(client, ws))["02 · Module B"]
    assert downloads(canvas_site) == ["/download/55"]


async def test_a_file_already_uploaded_under_its_name_is_adopted_not_fetched(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A class filled in by an earlier tool keeps its files, and none are doubled."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    ws = (await client.post("/workspaces", json={"name": "Bio"})).json()["id"]
    folder = (
        await client.post(f"/workspaces/{ws}/folders", json={"name": "01 · Module A"})
    ).json()["id"]
    uploaded = await client.post(
        f"/workspaces/{ws}/documents/upload",
        files={"files": ("Week1.pdf", PDF, "application/pdf")},
        data={"folder_id": str(folder)},
    )
    earlier = uploaded.json()["created"][0]["id"]

    assert await sync(client) == ws

    assert downloads(canvas_site) == []
    found = [
        d for d in (await documents(client, ws)).values() if d["title"] == "Week1.pdf"
    ]
    assert [d["id"] for d in found] == [earlier]


async def test_a_file_name_with_a_slash_is_titled_by_its_last_segment(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """SurfSense keeps only a name's last segment as the title."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {57: ("Unit 1/Slides.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[57])]

    ws = await sync(client)

    assert "Slides.pdf" in await documents(client, ws)


async def test_a_file_host_not_yet_allowed_is_asked_about_before_anything_is_fetched(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Nothing leaves the machine for a host the user has not allowed."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    data.file_host = "files.school.example"

    refused = await client.post("/canvas/sync", json={})

    assert refused.status_code == 403
    detail = refused.json()["detail"]
    assert detail["code"] == "egress_disabled"
    assert detail["hosts"] == ["files.school.example"]
    assert detail["purpose"] == "canvas"
    assert downloads(canvas_site) == []
    names = [w["name"] for w in (await client.get("/workspaces")).json()]
    assert "Bio" not in names
