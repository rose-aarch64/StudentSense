import pytest
from httpx import AsyncClient

from modules.canvas.client import CanvasClient
from modules.canvas.sync.snapshot import CourseSnapshot, read_course
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData
from tests.integration.canvas.test_sync_assignment_notes import lab
from tests.integration.canvas.test_sync_content import folders, page, start, sync
from tests.integration.canvas.test_sync_files import downloads

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n%a stand-in file\n"


def read(site: CanvasSite) -> CourseSnapshot:
    """What the sync reads of the stand-in school's one course, with no database."""
    with CanvasClient(site.base, GOOD_TOKEN) as canvas:
        return read_course(canvas, 1)


def set_up(site: CanvasSite) -> None:
    """A class whose texts link files: a module holds 55; 56 and 57 are linked only."""
    site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    data = site.course(1)
    # Distinct bytes: the same bytes twice are kept once.
    data.files = {
        55: ("Syllabus.pdf", PDF + b"55"),
        56: ("Handout.pdf", PDF + b"56"),
        57: ("Lab sheet.pdf", PDF + b"57"),
    }
    data.modules = [ModuleData(5, "Module A", files=[55])]
    data.syllabus = '<p><a href="/courses/1/files/55?wrap=1">policy</a></p>'
    data.pages = {
        "intro": page(
            11, "Intro", f'<a href="{site.base}/courses/1/files/56?verifier=x">h</a>'
        )
    }
    data.assignments = [
        lab(7, "Lab 1", '<a href="/courses/1/files/57/preview">sheet</a>')
    ]
    data.announcements = [
        {
            "id": 1,
            "title": "Hi",
            "posted_at": "2026-09-01T00:00:00Z",
            "message": '<a href="/courses/1/files/56">again</a>',
        }
    ]


def by_id(snapshot: CourseSnapshot) -> dict:
    """The snapshot's files by Canvas id."""
    return {f.file_id: f for f in snapshot.files}


def test_a_linked_file_is_read_once_and_a_module_file_is_not_read_twice(
    canvas_site: CanvasSite,
) -> None:
    """Linked from four texts, a file is still one file; a module's keeps its module."""
    set_up(canvas_site)

    snapshot = read(canvas_site)

    files = by_id(snapshot)
    assert sorted(files) == [55, 56, 57]
    assert len(snapshot.files) == 3
    assert files[55].module is not None
    assert files[56].module is None and files[57].module is None
    assert files[56].name == "Handout.pdf"
    assert files[56].size == len(PDF + b"56")


def test_an_announcement_attachment_is_read_as_a_linked_file(
    canvas_site: CanvasSite,
) -> None:
    """Canvas hands an announcement's attachment over with its signed link."""
    canvas_site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    data = canvas_site.course(1)
    data.files = {58: ("Notice.pdf", PDF)}
    data.announcements = [
        {
            "id": 1,
            "title": "Hi",
            "posted_at": "2026-09-01T00:00:00Z",
            "message": "<p>See attached</p>",
            "attachments": [
                {
                    "id": 58,
                    "display_name": "Notice.pdf",
                    "url": f"{canvas_site.base}/download/58",
                    "size": len(PDF),
                    "modified_at": "2026-09-01T00:00:00Z",
                }
            ],
        }
    ]

    snapshot = read(canvas_site)

    (ref,) = snapshot.files
    assert (ref.file_id, ref.name, ref.module) == (58, "Notice.pdf", None)
    assert ref.url == f"{canvas_site.base}/download/58"


def test_a_linked_file_of_an_unsupported_type_is_skipped_by_name(
    canvas_site: CanvasSite,
) -> None:
    """A .doc cannot be stored, so its Canvas link stays and the log can say so."""
    canvas_site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    data = canvas_site.course(1)
    data.files = {59: ("Old hours.doc", b"x")}
    data.syllabus = '<a href="/courses/1/files/59">hours</a>'

    snapshot = read(canvas_site)

    assert snapshot.files == []
    assert snapshot.skipped_files == ["Old hours.doc"]


def test_a_link_to_another_courses_file_or_host_is_not_read(
    canvas_site: CanvasSite,
) -> None:
    """Only this course's files on the school's own host are the token's to read."""
    canvas_site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    data = canvas_site.course(1)
    data.files = {60: ("Other.pdf", PDF)}
    data.syllabus = (
        '<a href="/courses/9/files/60">elsewhere</a> '
        '<a href="https://other.example/courses/1/files/60">abroad</a>'
    )

    snapshot = read(canvas_site)

    assert snapshot.files == []
    assert snapshot.skipped_files == []


def test_a_linked_file_canvas_refuses_is_skipped_and_the_read_goes_on(
    canvas_site: CanvasSite,
) -> None:
    """A locked file must not stop the class's sync."""
    canvas_site.courses = [{"id": 1, "name": "Bio", "term": {"name": "2026/FA"}}]
    data = canvas_site.course(1)
    data.files = {61: ("Kept.pdf", PDF)}
    data.syllabus = (
        '<a href="/courses/1/files/99">gone</a> <a href="/courses/1/files/61">kept</a>'
    )

    snapshot = read(canvas_site)

    assert [f.file_id for f in snapshot.files] == [61]
    assert snapshot.skipped_files == ["99"]


async def listing(client: AsyncClient, ws: int) -> list[dict]:
    """Every document of the workspace, as the Sources panel lists them."""
    listed = await client.get(f"/workspaces/{ws}/documents?limit=200")
    return listed.json()


async def test_a_linked_file_lands_in_the_canvas_files_folder(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A file no module holds still has a place; a module's file keeps its own."""
    await start(client, canvas_site)
    set_up(canvas_site)

    ws = await sync(client)

    held = await listing(client, ws)
    by_title = {d["title"]: d for d in held}
    named = await folders(client, ws)
    assert by_title["Handout.pdf"]["folder_id"] == named["Canvas files"]
    assert by_title["Lab sheet.pdf"]["folder_id"] == named["Canvas files"]
    assert by_title["Syllabus.pdf"]["folder_id"] == named["01 · Module A"]
    assert [d["title"] for d in held].count("Syllabus.pdf") == 1


async def test_a_class_with_no_linked_files_makes_no_canvas_files_folder(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """An empty folder would only be noise."""
    await start(client, canvas_site)
    canvas_site.course(1).syllabus = "<p>No links here</p>"

    ws = await sync(client)

    assert "Canvas files" not in await folders(client, ws)


async def test_a_second_sync_fetches_no_linked_file_again(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """What is held is filed, not downloaded again."""
    await start(client, canvas_site)
    set_up(canvas_site)
    await sync(client)

    await sync(client)

    assert sorted(downloads(canvas_site)) == [
        "/download/55",
        "/download/56",
        "/download/57",
    ]


async def test_a_renamed_canvas_files_folder_keeps_its_name(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Canvas has no name for the folder, so the student's is the one to keep."""
    await start(client, canvas_site)
    set_up(canvas_site)
    ws = await sync(client)
    folder = (await folders(client, ws))["Canvas files"]
    renamed = await client.patch(
        f"/workspaces/{ws}/folders/{folder}", json={"name": "Handouts"}
    )
    assert renamed.status_code == 200, renamed.text

    await sync(client)

    named = await folders(client, ws)
    assert named.get("Handouts") == folder
    assert "Canvas files" not in named


async def test_a_linked_file_on_a_host_not_yet_allowed_is_asked_about_first(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A linked file's signed link may name another host; nothing leaves until allowed."""
    await start(client, canvas_site)
    data = canvas_site.course(1)
    data.files = {56: ("Handout.pdf", PDF)}
    data.syllabus = '<a href="/courses/1/files/56">h</a>'
    data.file_host = "files.school.example"

    refused = await client.post("/canvas/sync", json={})

    assert refused.status_code == 403
    assert refused.json()["detail"]["hosts"] == ["files.school.example"]
    assert downloads(canvas_site) == []
