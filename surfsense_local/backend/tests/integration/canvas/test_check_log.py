import pytest
from httpx import AsyncClient

from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite, ModuleData

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n%a stand-in file\n"
EDITED = b"%PDF-1.4\n%the teacher changed it\n"


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


async def synced_with_a_file(client: AsyncClient, site: CanvasSite) -> None:
    """A synced class holding one file, which a test may then edit in Canvas."""
    site.courses = [course(1, "Bio")]
    data = site.course(1)
    data.files = {55: ("Week1.pdf", PDF)}
    data.modules = [ModuleData(5, "Module A", files=[55])]
    await connect(client, site)
    synced = await client.post("/canvas/sync", json={})
    assert synced.status_code == 200, synced.text


async def test_a_check_logs_a_line_per_class_with_counts(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """What the check compared, class by class."""
    await synced_with_a_file(client, canvas_site)
    canvas_site.course(1).edit_file(55, EDITED, "2026-11-20T00:00:00Z")

    checked = await client.get("/canvas/stale")

    assert checked.status_code == 200, checked.text
    log = await shown(client)
    assert (log["kind"], log["state"]) == ("check", "done")
    assert codes(log) == ["check_started", "class_checked", "finished"]
    assert log["entries"][1]["params"] == {"name": "Bio", "changed": 1, "gone": 0}
    assert log["entries"][2]["params"] == {"classes": 1, "errors": 0}


async def test_a_check_skips_a_class_that_was_never_synced(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """There is nothing kept to compare for a class not synced yet."""
    await synced_with_a_file(client, canvas_site)
    canvas_site.courses.append(course(2, "Photography"))

    await client.get("/canvas/stale")

    assert codes(await shown(client)).count("class_checked") == 1


async def test_a_check_that_cannot_ask_canvas_logs_why_it_stopped(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """A revoked token ends the check, and the log names the reason."""
    await synced_with_a_file(client, canvas_site)
    canvas_site.refusing = True

    refused = await client.get("/canvas/stale")

    assert refused.status_code == 409
    log = await shown(client)
    assert codes(log) == ["check_started", "stopped"]
    assert log["entries"][-1]["params"] == {"error": "canvas_token_refused"}
    assert log["state"] == "failed"


async def test_a_check_replaces_a_syncs_log(
    client: AsyncClient, canvas_site: CanvasSite
) -> None:
    """One log: the last run, whichever kind it was."""
    await synced_with_a_file(client, canvas_site)
    assert (await shown(client))["kind"] == "sync"

    await client.get("/canvas/stale")

    log = await shown(client)
    assert (log["kind"], log["run"]) == ("check", 2)
