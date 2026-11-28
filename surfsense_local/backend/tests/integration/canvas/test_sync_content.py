import pytest
from httpx import AsyncClient

from shared.queue import ingest_queue
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData

pytestmark = pytest.mark.integration


def page(page_id: int, title: str, body: str = "<p>Read ch. 1</p>") -> dict:
    """A course page as Canvas holds it."""
    return {"page_id": page_id, "title": title, "body": body}


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


async def content_of(client: AsyncClient, workspace_id: int, document_id: int) -> str:
    """A note's text."""
    detail = await client.get(f"/workspaces/{workspace_id}/documents/{document_id}")
    return detail.json()["content"]


async def test_the_syllabus_is_a_note_in_overview_with_its_markup_removed(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A model reads the words; the tags are noise."""
    course = await start(client, canvas_site)
    canvas_site.course(course).syllabus = "<h1>Rules</h1><p>Be <b>kind</b></p>"

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Syllabus"]
    assert note["folder_id"] == (await folders(client, ws))["Overview"]
    text = await content_of(client, ws, note["id"])
    assert "Be kind" in text and "<" not in text


async def test_a_relative_canvas_link_in_the_syllabus_becomes_the_schools_address(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A path in a note would resolve against this app and lead nowhere."""
    course = await start(client, canvas_site)
    canvas_site.course(
        course
    ).syllabus = '<p>Read <a href="/courses/1/files/9?wrap=1">the policy</a></p>'

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Syllabus"]
    text = await content_of(client, ws, note["id"])
    assert f"[the policy]({canvas_site.base}/courses/1/files/9?wrap=1)" in text


async def test_a_section_with_nothing_in_it_makes_no_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """An empty Announcements note would only be noise in search."""
    course = await start(client, canvas_site)
    canvas_site.course(course).syllabus = "<p>Hi</p>"

    ws = await sync(client)

    titles = set(await documents(client, ws))
    assert "Canvas · Syllabus" in titles
    assert "Canvas · Announcements" not in titles
    assert "Canvas · Assignments" not in titles


async def test_a_module_is_a_numbered_folder_and_its_page_a_note_inside_it(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Folders follow the course's own order, with the teacher's dates dropped."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.modules = [
        ModuleData(5, "08/28/26-09/28/26: Module A Intro", pages=["intro"]),
    ]

    ws = await sync(client)

    folder = (await folders(client, ws))["01 · Module A Intro"]
    note = (await documents(client, ws))["Canvas · Page · Intro"]
    assert note["folder_id"] == folder
    assert "Read ch. 1" in await content_of(client, ws, note["id"])


async def test_a_page_in_no_module_is_filed_under_unsorted(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """With the Pages tab on, a page can sit outside every module."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages_tab_disabled = False
    data.pages = {"loose": page(12, "Loose")}

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Page · Loose"]
    assert note["folder_id"] == (await folders(client, ws))["Unsorted"]


async def test_a_second_sync_changes_nothing_that_did_not_change(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """No duplicates, and no pointless re-reading of an unchanged note."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.modules = [ModuleData(5, "Module A", pages=["intro"])]
    ws = await sync(client)
    before = await documents(client, ws)
    queued = len(ingest_queue.pending())

    await sync(client)

    after = await documents(client, ws)
    assert {t: d["id"] for t, d in after.items()} == {
        t: d["id"] for t, d in before.items()
    }
    assert len(ingest_queue.pending()) == queued


async def test_a_page_edited_in_canvas_is_updated_and_read_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Search must not keep answering from the old text."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro", "<p>old words</p>")}
    data.modules = [ModuleData(5, "Module A", pages=["intro"])]
    ws = await sync(client)
    note = (await documents(client, ws))["Canvas · Page · Intro"]
    queued = len(ingest_queue.pending())

    data.pages["intro"]["body"] = "<p>new words</p>"
    await sync(client)

    assert "new words" in await content_of(client, ws, note["id"])
    assert len(ingest_queue.pending()) == queued + 1


async def test_a_retitled_page_keeps_its_note_and_takes_the_new_title(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The link is the page's id: the instructor swapping a placeholder's title is no new page."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"c4": page(21, "11/23/26 - Add Lessons C4 Slides", "<p>soon</p>")}
    data.modules = [ModuleData(5, "Module C", pages=["c4"])]
    ws = await sync(client)
    placeholder = (await documents(client, ws))[
        "Canvas · Page · 11/23/26 - Add Lessons C4 Slides"
    ]

    data.pages["c4"]["title"] = "C4 Lesson"
    await sync(client)

    after = await documents(client, ws)
    assert after["Canvas · Page · C4 Lesson"]["id"] == placeholder["id"]
    assert "Canvas · Page · 11/23/26 - Add Lessons C4 Slides" not in after


async def test_a_module_inserted_before_the_others_renumbers_without_remaking_anything(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The permanence the first prototype lacked: folders are found by module id."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.modules = [ModuleData(5, "Module A", pages=["intro"])]
    ws = await sync(client)
    folder_before = (await folders(client, ws))["01 · Module A"]
    note_before = (await documents(client, ws))["Canvas · Page · Intro"]

    data.modules.insert(0, ModuleData(4, "Welcome"))
    await sync(client)

    assert (await folders(client, ws))["02 · Module A"] == folder_before
    after = (await documents(client, ws))["Canvas · Page · Intro"]
    assert after["id"] == note_before["id"] and after["folder_id"] == folder_before


async def test_a_page_moved_to_another_module_moves_its_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Where a thing lives in Canvas is where it lives here."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.modules = [
        ModuleData(5, "Module A", pages=["intro"]),
        ModuleData(6, "Module B"),
    ]
    ws = await sync(client)
    note = (await documents(client, ws))["Canvas · Page · Intro"]

    data.modules[0].pages = []
    data.modules[1].pages = ["intro"]
    await sync(client)

    moved = (await documents(client, ws))["Canvas · Page · Intro"]
    assert moved["id"] == note["id"]
    assert moved["folder_id"] == (await folders(client, ws))["02 · Module B"]


async def test_what_the_user_made_earlier_under_the_same_names_is_adopted(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A class set up by an earlier tool is not remade beside itself."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.modules = [ModuleData(5, "Module A", pages=["intro"])]
    made = await client.post("/workspaces", json={"name": "Bio"})
    ws = made.json()["id"]
    folder = await client.post(
        f"/workspaces/{ws}/folders", json={"name": "01 · Module A"}
    )
    note = await client.post(
        f"/workspaces/{ws}/documents",
        json={
            "title": "Canvas · Page · Intro",
            "content": "old",
            "folder_id": folder.json()["id"],
        },
    )

    assert await sync(client) == ws

    found = await documents(client, ws)
    assert found["Canvas · Page · Intro"]["id"] == note.json()["id"]
    assert len([t for t in found if t.startswith("Canvas · Page")]) == 1
    assert (await folders(client, ws))["01 · Module A"] == folder.json()["id"]


async def test_a_page_removed_from_canvas_is_left_in_place(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Nothing the sync made is ever deleted for Canvas having dropped it."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.pages = {"intro": page(11, "Intro")}
    data.modules = [ModuleData(5, "Module A", pages=["intro"])]
    ws = await sync(client)

    data.modules[0].pages = []
    del data.pages["intro"]
    await sync(client)

    assert "Canvas · Page · Intro" in await documents(client, ws)


async def test_external_links_are_kept_with_their_urls_in_a_links_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The Modules note names a link; only its address lets anyone follow it."""
    course = await start(client, canvas_site)
    data = canvas_site.course(course)
    data.modules = [
        ModuleData(
            5,
            "Module A",
            links=[("Kost's Blog", "https://example.org/blog")],
        ),
        ModuleData(6, "Module B"),
    ]

    ws = await sync(client)

    note = (await documents(client, ws))["Canvas · Links"]
    assert note["folder_id"] == (await folders(client, ws))["Overview"]
    text = await content_of(client, ws, note["id"])
    assert "Module A" in text
    assert "[Kost's Blog](https://example.org/blog)" in text
    assert "Module B" not in text


async def test_a_course_with_no_external_links_makes_no_links_note(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """An empty Links note would only be noise in search."""
    course = await start(client, canvas_site)
    canvas_site.course(course).modules = [ModuleData(5, "Module A")]

    ws = await sync(client)

    assert "Canvas · Links" not in await documents(client, ws)
