import pytest
from httpx import AsyncClient

from tests.integration.canvas.conftest import CanvasSite, ModuleData
from tests.integration.canvas.test_sync_content import folders, start, sync

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n%a stand-in file\n"


async def import_book(client: AsyncClient, ws: int, folder_id: int, name: str) -> int:
    """What the Import textbook button does: upload one file into the folder."""
    uploaded = await client.post(
        f"/workspaces/{ws}/documents/upload",
        files=[("files", (name, PDF, "application/pdf"))],
        data={"folder_id": str(folder_id)},
    )
    assert uploaded.status_code == 201, uploaded.text
    return uploaded.json()["created"][0]["id"]


async def listing(client: AsyncClient, ws: int) -> list[dict]:
    """Every document of the workspace, as the Sources panel lists them."""
    listed = await client.get(f"/workspaces/{ws}/documents?limit=200")
    return listed.json()


async def test_each_synced_class_gets_a_textbook_folder(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A place to import the book exists before there is a book."""
    await start(client, canvas_site)

    ws = await sync(client)

    assert "Textbook" in await folders(client, ws)


async def test_a_second_sync_leaves_the_textbook_folder_and_its_book(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The sync only touches what it made; an imported book stays where it is."""
    await start(client, canvas_site)
    ws = await sync(client)
    textbook = (await folders(client, ws))["Textbook"]
    book = await import_book(client, ws, textbook, "Networks.pdf")

    assert await sync(client) == ws

    assert (await folders(client, ws))["Textbook"] == textbook
    kept = [d for d in await listing(client, ws) if d["id"] == book]
    assert [d["folder_id"] for d in kept] == [textbook]


async def test_a_renamed_textbook_folder_keeps_the_students_name(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas has no name for the folder, so the student's name is the one to keep."""
    await start(client, canvas_site)
    ws = await sync(client)
    textbook = (await folders(client, ws))["Textbook"]
    renamed = await client.patch(
        f"/workspaces/{ws}/folders/{textbook}", json={"name": "Networks book"}
    )
    assert renamed.status_code == 200, renamed.text

    await sync(client)

    named = await folders(client, ws)
    assert named.get("Networks book") == textbook
    assert "Textbook" not in named


async def test_a_book_is_not_adopted_as_a_module_file_of_the_same_name(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A module file is looked for in the module folders only, never in Textbook."""
    course = await start(client, canvas_site)
    ws = await sync(client)
    textbook = (await folders(client, ws))["Textbook"]
    book = await import_book(client, ws, textbook, "Week1.pdf")
    data = canvas_site.course(course)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]

    await sync(client)

    named = [d for d in await listing(client, ws) if d["title"] == "Week1.pdf"]
    assert len(named) == 2
    assert {d["id"]: d["folder_id"] for d in named}[book] == textbook
