from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from modules.canvas.client import (
    CanvasClient,
    CanvasNotFoundError,
    CanvasRefusedError,
    CanvasUnreachableError,
)
from modules.canvas.download import download
from tests.mcp_test_server import serving

pytestmark = pytest.mark.integration


@dataclass
class Site:
    base: str
    asked: list[Request] = field(default_factory=list)


def canvas_app(asked: list[Request]) -> Starlette:
    """The few Canvas behaviours the client has to handle, each on its own route."""

    async def courses(request: Request) -> Response:
        asked.append(request)
        if request.query_params.get("page") == "2":
            return JSONResponse([{"id": 3}])
        next_page = f'<{request.base_url}api/v1/courses?page=2>; rel="next"'
        return JSONResponse([{"id": 1}, {"id": 2}], headers={"Link": next_page})

    async def gone(request: Request) -> Response:
        asked.append(request)
        reason = {"message": "That page has been disabled for this course"}
        return JSONResponse(reason, 404)

    async def denied(request: Request) -> Response:
        asked.append(request)
        return JSONResponse({"errors": []}, 401)

    async def elsewhere(request: Request) -> Response:
        asked.append(request)
        away = '<http://127.0.0.2:9/api/v1/x?page=2>; rel="next"'
        return JSONResponse([{"id": 1}], headers={"Link": away})

    async def file(request: Request) -> Response:
        asked.append(request)
        return Response(b"%PDF-bytes", media_type="application/pdf")

    async def signed(request: Request) -> Response:
        asked.append(request)
        where = f"{request.base_url}file"
        return Response(status_code=302, headers={"Location": where})

    return Starlette(
        routes=[
            Route("/api/v1/courses", courses),
            Route("/api/v1/gone", gone),
            Route("/api/v1/denied", denied),
            Route("/api/v1/elsewhere", elsewhere),
            Route("/file", file),
            Route("/signed", signed),
        ]
    )


@pytest.fixture
def site() -> Iterator[Site]:
    """A Canvas on loopback, recording every request it gets."""
    asked: list[Request] = []
    with serving(canvas_app(asked)) as base:
        yield Site(base, asked)


def test_every_page_of_a_listing_is_collected_through_its_next_links(
    site: Site,
) -> None:
    """Canvas pages its lists; a student with many courses must not lose the later ones."""
    with CanvasClient(site.base, "tok") as canvas:
        courses = canvas.get_all("/courses")

    assert [c["id"] for c in courses] == [1, 2, 3]


def test_the_first_page_asks_for_a_hundred_and_the_token_goes_with_each_page(
    site: Site,
) -> None:
    """A big page size keeps the round trips few; every page is still the user's own."""
    with CanvasClient(site.base, "tok") as canvas:
        canvas.get_all("/courses")

    first, second = site.asked
    assert first.query_params["per_page"] == "100"
    bearer = "Bearer tok"
    assert first.headers["authorization"] == second.headers["authorization"] == bearer


def test_a_missing_resource_says_what_canvas_said(site: Site) -> None:
    """A course with its Pages tab off answers 404 with a reason the sync reads."""
    with (
        CanvasClient(site.base, "tok") as canvas,
        pytest.raises(CanvasNotFoundError) as missing,
    ):
        canvas.get_all("/gone")

    assert "disabled for this course" in str(missing.value)


def test_a_refused_token_is_its_own_error(site: Site) -> None:
    """The sync stops and says so, instead of treating it as an empty course."""
    with CanvasClient(site.base, "tok") as canvas, pytest.raises(CanvasRefusedError):
        canvas.get_all("/denied")


def test_a_next_link_to_another_host_is_never_followed(site: Site) -> None:
    """The token belongs to the school; a Link header cannot send it elsewhere."""
    with (
        CanvasClient(site.base, "tok") as canvas,
        pytest.raises(CanvasUnreachableError),
    ):
        canvas.get_all("/elsewhere")

    assert len(site.asked) == 1


def test_a_file_download_never_carries_the_canvas_token(site: Site) -> None:
    """Canvas signs the link and it may sit on another host, so the token stays home."""
    data = download(f"{site.base}/signed")

    assert data == b"%PDF-bytes"
    assert all("authorization" not in r.headers for r in site.asked)
