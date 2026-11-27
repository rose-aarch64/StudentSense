from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from httpx import AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from tests.mcp_test_server import serving

GOOD_TOKEN = "good-token"


@dataclass
class ModuleData:
    """A Canvas module and what it holds, by the ids the course's pages and files have."""

    id: int
    name: str
    pages: list[str] = field(default_factory=list)
    files: list[int] = field(default_factory=list)
    # (title, url) of each external link the module holds.
    links: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class CourseData:
    """Everything one course holds, in the terms a test sets it up."""

    syllabus: str = ""
    assignments: list[dict] = field(default_factory=list)
    announcements: list[dict] = field(default_factory=list)
    modules: list[ModuleData] = field(default_factory=list)
    # slug -> {"page_id": int, "title": str, "body": str}
    pages: dict[str, dict] = field(default_factory=dict)
    pages_tab_disabled: bool = True
    # A course Canvas can no longer find, as one concluded or removed since a sync.
    assignments_missing: bool = False
    # file id -> (name, bytes)
    files: dict[int, tuple[str, bytes]] = field(default_factory=dict)
    # Where signed download links point, when not at this Canvas itself.
    file_host: str | None = None
    # file id -> when Canvas says it last changed
    file_modified: dict[int, str] = field(default_factory=dict)

    def edit_file(self, file_id: int, data: bytes, modified: str) -> None:
        """Change a file in Canvas the way a teacher re-uploading it does."""
        name = self.files[file_id][0]
        self.files[file_id] = (name, data)
        self.file_modified[file_id] = modified


@dataclass
class CanvasSite:
    base: str
    asked: list[Request] = field(default_factory=list)
    # What the school's Canvas holds; a test changes it between syncs.
    courses: list[dict] = field(default_factory=list)
    data: dict[int, CourseData] = field(default_factory=dict)
    # Answer every token as Canvas does a revoked one.
    refusing: bool = False
    # File ids whose signed link answers with a server error.
    broken_downloads: set[int] = field(default_factory=set)

    def course(self, course_id: int) -> CourseData:
        return self.data.setdefault(course_id, CourseData())


def canvas_app(site: CanvasSite) -> Starlette:
    """The Canvas routes the connection and the sync read, answering as Canvas does."""

    def signed_in(request: Request) -> bool:
        site.asked.append(request)
        token = request.headers.get("authorization")
        return not site.refusing and token == f"Bearer {GOOD_TOKEN}"

    refused = JSONResponse({"errors": [{"message": "Invalid access token."}]}, 401)

    def guarded(handler):
        async def route(request: Request) -> Response:
            if not signed_in(request):
                return refused
            return await handler(request)

        return route

    def course_of(request: Request) -> CourseData:
        return site.course(int(request.path_params["course_id"]))

    async def whoami(request: Request) -> Response:
        return JSONResponse({"id": 7, "name": "Rose B"})

    async def courses(request: Request) -> Response:
        return JSONResponse(site.courses)

    async def one_course(request: Request) -> Response:
        course = course_of(request)
        course_id = int(request.path_params["course_id"])
        return JSONResponse({"id": course_id, "syllabus_body": course.syllabus})

    async def assignments(request: Request) -> Response:
        course = course_of(request)
        if course.assignments_missing:
            return JSONResponse({"message": "not found"}, 404)
        return JSONResponse(course.assignments)

    async def announcements(request: Request) -> Response:
        code = request.query_params.get("context_codes[]", "")
        course_id = int(code.removeprefix("course_") or 0)
        return JSONResponse(site.course(course_id).announcements)

    async def modules(request: Request) -> Response:
        course = course_of(request)
        listed = []
        for module in course.modules:
            items = (
                [
                    {
                        "type": "Page",
                        "title": course.pages[slug]["title"],
                        "page_url": slug,
                    }
                    for slug in module.pages
                ]
                + [
                    {"type": "File", "title": course.files[fid][0], "content_id": fid}
                    for fid in module.files
                ]
                + [
                    {"type": "ExternalUrl", "title": title, "external_url": url}
                    for title, url in module.links
                ]
            )
            listed.append({"id": module.id, "name": module.name, "items": items})
        return JSONResponse(listed)

    async def pages(request: Request) -> Response:
        course = course_of(request)
        if course.pages_tab_disabled:
            reason = {"message": "That page has been disabled for this course"}
            return JSONResponse(reason, 404)
        return JSONResponse([{"url": slug, **p} for slug, p in course.pages.items()])

    async def page(request: Request) -> Response:
        found = course_of(request).pages.get(request.path_params["slug"])
        if found is None:
            return JSONResponse({"message": "not found"}, 404)
        return JSONResponse({"url": request.path_params["slug"], **found})

    async def file_detail(request: Request) -> Response:
        course = course_of(request)
        file_id = int(request.path_params["file_id"])
        if file_id not in course.files:
            return JSONResponse({"message": "not found"}, 404)
        name, data = course.files[file_id]
        origin = (
            f"https://{course.file_host}/" if course.file_host else request.base_url
        )
        return JSONResponse(
            {
                "id": file_id,
                "display_name": name,
                "size": len(data),
                "modified_at": course.file_modified.get(
                    file_id, "2026-11-01T00:00:00Z"
                ),
                "url": f"{origin}download/{file_id}",
                "locked_for_user": False,
            }
        )

    async def download(request: Request) -> Response:
        # A signed link: no token is expected, and none must be sent.
        site.asked.append(request)
        file_id = int(request.path_params["file_id"])
        if file_id in site.broken_downloads:
            return Response(status_code=500)
        for course in site.data.values():
            if file_id in course.files:
                return Response(course.files[file_id][1])
        return Response(status_code=404)

    api = "/api/v1"
    return Starlette(
        routes=[
            Route(f"{api}/users/self", guarded(whoami)),
            Route(f"{api}/courses", guarded(courses)),
            Route(f"{api}/courses/{{course_id:int}}", guarded(one_course)),
            Route(f"{api}/courses/{{course_id:int}}/assignments", guarded(assignments)),
            Route(f"{api}/announcements", guarded(announcements)),
            Route(f"{api}/courses/{{course_id:int}}/modules", guarded(modules)),
            Route(f"{api}/courses/{{course_id:int}}/pages", guarded(pages)),
            Route(f"{api}/courses/{{course_id:int}}/pages/{{slug}}", guarded(page)),
            Route(
                f"{api}/courses/{{course_id:int}}/files/{{file_id:int}}",
                guarded(file_detail),
            ),
            Route("/download/{file_id:int}", download),
        ]
    )


@pytest.fixture
def canvas_site() -> Iterator[CanvasSite]:
    """A school's Canvas on loopback: reaching it needs no consent."""
    site = CanvasSite(base="")
    with serving(canvas_app(site)) as base:
        site.base = base
        yield site


async def allow(client: AsyncClient, *hosts: str) -> None:
    """As the consent prompt's Allow does."""
    allowed = await client.put(
        "/egress",
        json={"destinations": [f"host:{host}" for host in hosts], "enabled": True},
    )
    assert allowed.status_code == 200, allowed.text
