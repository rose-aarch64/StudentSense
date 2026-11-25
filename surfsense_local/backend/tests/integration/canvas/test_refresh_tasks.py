from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from modules.canvas.refresh import run as refresh_run
from modules.canvas.refresh.run import RefreshResult, refresh_tasks
from modules.egress.service import EgressDeniedError
from shared.db import create_session_factory
from tests.integration.canvas.conftest import GOOD_TOKEN, CanvasSite

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def assignment(
    assignment_id: int,
    name: str,
    due: str | None = "2026-12-01T05:00:00Z",
    state: str = "unsubmitted",
) -> dict:
    """An assignment as Canvas lists it, with the student's own submission."""
    return {
        "id": assignment_id,
        "name": name,
        "due_at": due,
        "submission": {"workflow_state": state},
    }


def course(course_id: int, name: str) -> dict:
    """A course as Canvas lists it, in a term with no dates."""
    return {"id": course_id, "name": name, "term": {"name": "2026/FA"}}


@pytest.fixture
def factory(engine: Engine) -> sessionmaker[Session]:
    """The session factory the refresh is handed, over the test's database."""
    return create_session_factory(engine)


async def start(client: AsyncClient, site: CanvasSite) -> int:
    """Connect the stand-in school, which has one course, and return its Canvas id."""
    site.courses = [course(1, "Bio")]
    connected = await client.put(
        "/canvas/connection", json={"base_url": site.base, "token": GOOD_TOKEN}
    )
    assert connected.status_code == 200, connected.text
    return 1


async def sync(client: AsyncClient) -> list[int]:
    """Sync, and return the workspace id of each course, in order."""
    synced = await client.post("/canvas/sync", json={})
    assert synced.status_code == 200, synced.text
    return [c["workspace_id"] for c in synced.json()["courses"]]


async def tasks(client: AsyncClient, workspace_id: int) -> dict[str, dict]:
    """The workspace's tasks by title."""
    listed = await client.get("/todos", params={"workspace_id": workspace_id})
    return {t["title"]: t for t in listed.json()}


def last_pass(engine: Engine) -> tuple:
    """What the connection row says about the last refresh: when, and the error."""
    with engine.begin() as connection:
        return tuple(
            connection.execute(
                text("SELECT refreshed_at, refresh_error FROM canvas_connection")
            ).one()
        )


def paths_asked_since(site: CanvasSite, mark: int) -> list[str]:
    """The Canvas paths requested after `mark` requests had been seen."""
    return [request.url.path for request in site.asked[mark:]]


async def test_a_refresh_updates_the_tasks_of_a_synced_class_and_reads_nothing_else(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """New work, a moved due date and a handed-in assignment, without a full sync."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    data.assignments = [
        assignment(31, "Lab 1", due="2026-12-08T05:00:00Z", state="submitted"),
        assignment(32, "Lab 2"),
    ]
    mark = len(canvas_site.asked)

    result = refresh_tasks(factory, NOW)

    assert result == RefreshResult(classes=1, error=None)
    listed = await tasks(client, workspace)
    assert listed["Lab 1"]["due_at"].startswith("2026-12-08T05:00:00")
    assert listed["Lab 1"]["done"] is True
    assert "Lab 2" in listed
    paths = paths_asked_since(canvas_site, mark)
    assert paths
    assert all(p.endswith(("/courses", "/courses/1/assignments")) for p in paths)


async def test_a_class_with_no_workspace_is_skipped(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """A class not synced yet needs a full sync; the refresh makes nothing."""
    await start(client, canvas_site)
    await sync(client)
    canvas_site.courses.append(course(2, "Photography"))
    before = (await client.get("/workspaces")).json()
    mark = len(canvas_site.asked)

    result = refresh_tasks(factory, NOW)

    assert result.classes == 1
    assert (await client.get("/workspaces")).json() == before
    assert not any("/courses/2" in p for p in paths_asked_since(canvas_site, mark))


async def test_a_class_outside_the_current_term_is_skipped(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """Last term's classes are left alone, as a sync leaves them."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    canvas_site.courses[0]["term"] = {
        "name": "2026/SP",
        "start_at": "2026-01-01T00:00:00Z",
        "end_at": "2026-05-01T00:00:00Z",
    }
    data.assignments = [assignment(31, "Lab 1", due="2026-12-08T05:00:00Z")]
    mark = len(canvas_site.asked)

    result = refresh_tasks(factory, NOW)

    assert result.classes == 0
    assert not any(
        p.endswith("/assignments") for p in paths_asked_since(canvas_site, mark)
    )
    assert (await tasks(client, workspace))["Lab 1"]["due_at"].startswith("2026-12-01")


async def test_a_task_the_user_deleted_stays_deleted(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """The refresh never brings back what the student removed."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    await client.delete(f"/todos/{(await tasks(client, workspace))['Lab 1']['id']}")

    refresh_tasks(factory, NOW)

    assert "Lab 1" not in await tasks(client, workspace)


async def test_a_check_the_user_made_stays_checked(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """Canvas may mark a task done; it never takes a student's check away."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    task = (await tasks(client, workspace))["Lab 1"]
    await client.patch(f"/todos/{task['id']}", json={"done": True})

    refresh_tasks(factory, NOW)

    assert (await tasks(client, workspace))["Lab 1"]["done"] is True


async def test_a_handed_in_task_the_user_unchecked_is_checked_again(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """Pins the sync's rule: work handed in marks an unchecked task done."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1", state="submitted")]
    (workspace,) = await sync(client)
    task = (await tasks(client, workspace))["Lab 1"]
    await client.patch(f"/todos/{task['id']}", json={"done": False})

    refresh_tasks(factory, NOW)

    assert (await tasks(client, workspace))["Lab 1"]["done"] is True


async def test_a_removed_due_date_is_cleared_and_a_new_undated_assignment_is_kept(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """Undated work is still work, and a date taken off in Canvas goes off here."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    data.assignments = [
        assignment(31, "Lab 1", due=None),
        assignment(32, "Reading", due=None),
    ]

    refresh_tasks(factory, NOW)

    listed = await tasks(client, workspace)
    assert listed["Lab 1"]["due_at"] is None
    assert listed["Reading"]["due_at"] is None


async def test_a_class_canvas_cannot_find_is_skipped_and_the_rest_still_refresh(
    client: AsyncClient, canvas_site: CanvasSite, factory: sessionmaker[Session]
) -> None:
    """One concluded course must not stop the others."""
    await start(client, canvas_site)
    canvas_site.courses.append(course(2, "Photography"))
    canvas_site.course(1).assignments = [assignment(31, "Lab 1")]
    canvas_site.course(2).assignments = [assignment(41, "Shoot 1")]
    first, second = await sync(client)
    canvas_site.course(1).assignments_missing = True
    canvas_site.course(2).assignments = [
        assignment(41, "Shoot 1", due="2026-12-08T05:00:00Z")
    ]

    result = refresh_tasks(factory, NOW)

    assert result == RefreshResult(classes=1, error=None)
    assert (await tasks(client, second))["Shoot 1"]["due_at"].startswith("2026-12-08")
    assert (await tasks(client, first))["Lab 1"]["due_at"].startswith("2026-12-01")


async def test_success_records_the_time_and_clears_an_earlier_error(
    client: AsyncClient,
    canvas_site: CanvasSite,
    factory: sessionmaker[Session],
    engine: Engine,
) -> None:
    """Settings shows when it last worked, and no stale complaint."""
    await start(client, canvas_site)
    await sync(client)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE canvas_connection SET refresh_error = 'canvas_unreachable'")
        )

    refresh_tasks(factory, NOW)

    refreshed_at, error = last_pass(engine)
    assert refreshed_at is not None
    assert error is None
    shown = (await client.get("/canvas/connection")).json()
    assert shown["refreshed_at"].endswith("Z")


async def test_a_refused_token_records_its_code_and_changes_no_task(
    client: AsyncClient,
    canvas_site: CanvasSite,
    factory: sessionmaker[Session],
    engine: Engine,
) -> None:
    """A revoked token is told to the user, and the list is left as it was."""
    data = canvas_site.course(await start(client, canvas_site))
    data.assignments = [assignment(31, "Lab 1")]
    (workspace,) = await sync(client)
    canvas_site.refusing = True
    data.assignments = [assignment(31, "Lab 1", due="2026-12-08T05:00:00Z")]

    result = refresh_tasks(factory, NOW)

    assert result == RefreshResult(classes=0, error="canvas_token_refused")
    assert last_pass(engine) == (None, "canvas_token_refused")
    assert (await tasks(client, workspace))["Lab 1"]["due_at"].startswith("2026-12-01")


async def test_withdrawn_consent_records_egress_disabled(
    client: AsyncClient,
    canvas_site: CanvasSite,
    factory: sessionmaker[Session],
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching the school off in Settings stops the refresh at once.

    The stand-in school is on loopback, which no consent covers, so the refusal
    is raised where the connection is read, as a real school's host would.
    """
    await start(client, canvas_site)
    await sync(client)
    mark = len(canvas_site.asked)

    def refused(_factory: sessionmaker[Session]) -> tuple[str, str]:
        raise EgressDeniedError("host:school.example")

    monkeypatch.setattr(refresh_run, "read_connection", refused)

    result = refresh_tasks(factory, NOW)

    assert result == RefreshResult(classes=0, error="egress_disabled")
    assert last_pass(engine) == (None, "egress_disabled")
    assert len(canvas_site.asked) == mark


async def test_with_no_connection_it_does_nothing(
    factory: sessionmaker[Session],
) -> None:
    """There is no row to record anything on, and nothing to ask."""
    assert refresh_tasks(factory, NOW) == RefreshResult(
        classes=0, error="canvas_not_connected"
    )
