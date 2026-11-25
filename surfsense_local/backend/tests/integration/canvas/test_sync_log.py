import pytest
from httpx import AsyncClient

from modules.canvas import client as canvas_client
from modules.canvas.sync import run as sync_run
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n%a stand-in file\n"
OTHER_PDF = b"%PDF-1.4\n%another stand-in file\n"


def course(course_id: int, name: str) -> dict:
    """A course as Canvas lists it, in a term with no dates."""
    return {"id": course_id, "name": name, "term": {"name": "2026/FA"}}


async def connect(client: AsyncClient, site: CanvasSite) -> None:
    """Connect the stand-in school with its good token."""
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text


async def shown(client: AsyncClient) -> dict:
    """The log as the panel reads it."""
    return (await client.get("/canvas/log")).json()


def codes(log: dict) -> list[str]:
    """The codes of the log's lines, in order."""
    return [entry["code"] for entry in log["entries"]]


def first(log: dict, code: str) -> dict:
    """The first line with this code."""
    return next(entry for entry in log["entries"] if entry["code"] == code)


async def test_a_sync_logs_each_class_with_what_it_read(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The user sees what came from Canvas, class by class."""
    canvas_site.courses = [course(1, "Bio")]
    data = canvas_site.course(1)
    data.assignments = [
        {"id": 31, "name": "Lab 1", "due_at": None, "submission": {}},
        {"id": 32, "name": "Lab 2", "due_at": None, "submission": {}},
    ]
    data.announcements = [{"id": 1, "title": "Hi", "message": "<p>Hi</p>"}]
    data.pages_tab_disabled = False
    data.pages = {"intro": {"page_id": 11, "title": "Intro", "body": "<p>x</p>"}}
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", pages=["intro"], files=[55])]
    await connect(client, canvas_site)

    synced = await client.post("/canvas/sync", json={})

    assert synced.status_code == 200, synced.text
    log = await shown(client)
    assert codes(log) == [
        "sync_started",
        "class_started",
        "class_read",
        "file_kept",
        "finished",
    ]
    assert first(log, "class_started")["params"] == {"name": "Bio"}
    assert first(log, "class_read")["params"] == {
        "name": "Bio",
        "assignments": 2,
        "announcements": 1,
        "modules": 1,
        "pages": 1,
        "files": 1,
    }
    assert first(log, "file_kept")["params"] == {"name": "Week1.pdf"}
    assert first(log, "finished")["params"] == {"classes": 1, "errors": 0}
    assert (log["kind"], log["state"]) == ("sync", "done")


async def test_a_course_with_its_pages_tab_off_says_so(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Its pages are still read, through the modules, and the log says how."""
    canvas_site.courses = [course(1, "Bio")]
    await connect(client, canvas_site)

    await client.post("/canvas/sync", json={})

    assert first(await shown(client), "pages_tab_off")["params"] == {"name": "Bio"}


async def test_a_file_that_cannot_be_downloaded_is_an_error_line_and_the_rest_continue(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """One bad link is told to the user and does not stop the others."""
    canvas_site.courses = [course(1, "Bio")]
    data = canvas_site.course(1)
    data.files = {55: ("A.pdf", PDF), 56: ("B.pdf", OTHER_PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55, 56])]
    canvas_site.broken_downloads = {55}
    await connect(client, canvas_site)

    synced = await client.post("/canvas/sync", json={})

    assert synced.status_code == 200, synced.text
    log = await shown(client)
    failed = first(log, "file_failed")
    assert (failed["level"], failed["params"]) == ("error", {"name": "A.pdf"})
    assert first(log, "file_kept")["params"] == {"name": "B.pdf"}
    assert first(log, "finished")["params"] == {"classes": 1, "errors": 1}


async def test_a_file_the_same_as_one_already_held_is_skipped_not_failed(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Two files with the same bytes in one folder keep one: not an error."""
    canvas_site.courses = [course(1, "Bio")]
    data = canvas_site.course(1)
    data.files = {55: ("A.pdf", PDF), 56: ("B.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55, 56])]
    await connect(client, canvas_site)

    await client.post("/canvas/sync", json={})

    log = await shown(client)
    assert codes(log).count("file_kept") == 1
    skipped = first(log, "file_skipped")
    assert (skipped["level"], skipped["params"]) == ("info", {"name": "B.pdf"})
    assert first(log, "finished")["params"]["errors"] == 0


async def test_a_second_sync_does_not_log_a_file_it_already_holds(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Only what is pulled is logged."""
    canvas_site.courses = [course(1, "Bio")]
    data = canvas_site.course(1)
    data.files = {55: ("A.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    await connect(client, canvas_site)
    await client.post("/canvas/sync", json={})

    await client.post("/canvas/sync", json={})

    log = await shown(client)
    assert "file_kept" not in codes(log)
    assert "file_skipped" not in codes(log)


async def test_a_sync_with_no_connection_logs_why_it_stopped(
    client: AsyncClient,
) -> None:
    """The log's last line names the reason, in the routes' own code."""
    refused = await client.post("/canvas/sync", json={})

    assert refused.status_code == 409
    log = await shown(client)
    assert log["state"] == "failed"
    assert log["entries"][-1]["code"] == "stopped"
    assert log["entries"][-1]["level"] == "error"
    assert log["entries"][-1]["params"] == {"error": "canvas_not_connected"}


async def test_a_refused_token_stops_with_its_code(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A revoked token ends the run at once, and the log says so."""
    canvas_site.courses = [course(1, "Bio")]
    await connect(client, canvas_site)
    canvas_site.refusing = True

    refused = await client.post("/canvas/sync", json={})

    assert refused.status_code == 409
    log = await shown(client)
    assert codes(log) == ["sync_started", "stopped"]
    assert log["entries"][-1]["params"] == {"error": "canvas_token_refused"}
    assert log["state"] == "failed"


async def test_a_run_that_stops_partway_keeps_the_lines_before_it(
    client: AsyncClient, canvas_site: CanvasSite, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What was read before the failure stays on screen."""
    canvas_site.courses = [course(1, "Bio"), course(2, "Photography")]
    canvas_site.course(1).pages_tab_disabled = False
    await connect(client, canvas_site)
    real = sync_run.read_course

    def flaky(canvas: canvas_client.CanvasClient, course_id: int):
        if course_id == 2:
            raise canvas_client.CanvasUnreachableError("down")
        return real(canvas, course_id)

    monkeypatch.setattr(sync_run, "read_course", flaky)

    stopped = await client.post("/canvas/sync", json={})

    assert stopped.status_code == 502
    log = await shown(client)
    assert codes(log) == [
        "sync_started",
        "class_started",
        "class_read",
        "class_started",
        "stopped",
    ]
    assert log["entries"][-1]["params"] == {"error": "canvas_unreachable"}
    assert log["state"] == "failed"


async def test_a_new_run_replaces_the_old_log(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """The log is the last run, not a history."""
    canvas_site.courses = [course(1, "Bio")]
    await connect(client, canvas_site)
    await client.post("/canvas/sync", json={})
    once = await shown(client)

    await client.post("/canvas/sync", json={})

    twice = await shown(client)
    assert (once["run"], twice["run"]) == (1, 2)
    assert twice["entries"][0]["n"] == 1
    assert twice["entries"][0]["code"] == "sync_started"
    assert len(twice["entries"]) == len(once["entries"])


async def test_the_log_never_holds_the_token_a_link_or_the_address(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """Names and counts only: nothing that could be used elsewhere."""
    canvas_site.courses = [course(1, "Bio")]
    data = canvas_site.course(1)
    data.files = {55: ("A.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    await connect(client, canvas_site)
    await client.post("/canvas/sync", json={})

    text = (await client.get("/canvas/log")).text

    assert GOOD_TOKEN not in text
    assert "/download/" not in text
    assert canvas_site.base not in text
