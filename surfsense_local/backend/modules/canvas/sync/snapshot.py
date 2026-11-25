from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import quote

from modules.canvas.client import CanvasClient, CanvasNotFoundError
from modules.canvas.html_text import html_to_text
from modules.documents.storage import SUPPORTED_UPLOAD_SUFFIXES


@dataclass(frozen=True)
class Module:
    id: int
    number: int
    name: str
    items: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class Page:
    page_id: int
    slug: str
    title: str
    body: str
    # The first module holding it; None for a page in none.
    module: Module | None


@dataclass(frozen=True)
class FileRef:
    """A file a module holds, with the signed link to fetch it by."""

    file_id: int
    name: str
    url: str
    module: Module
    # Canvas's own account of the file's version: a change in either means an edit.
    size: int | None
    modified_at: str | None


@dataclass(frozen=True)
class CourseSnapshot:
    """What one course held when it was read, with no database involved."""

    syllabus: str
    assignments: list[dict]
    announcements: list[dict]
    modules: list[Module]
    pages: list[Page]
    files: list[FileRef]
    # The course turned its Pages tab off, so its pages came through its modules.
    pages_tab_off: bool = False


def read_course(canvas: CanvasClient, course_id: int) -> CourseSnapshot:
    course = canvas.get_one(f"/courses/{course_id}", {"include[]": "syllabus_body"})
    modules = read_modules(canvas, course_id)
    pages, pages_tab_off = _read_pages(canvas, course_id, modules)
    return CourseSnapshot(
        syllabus=html_to_text(course.get("syllabus_body")),
        assignments=canvas.get_all(
            f"/courses/{course_id}/assignments", {"include[]": "submission"}
        ),
        announcements=canvas.get_all(
            "/announcements", {"context_codes[]": f"course_{course_id}"}
        ),
        modules=modules,
        pages=pages,
        files=_read_files(canvas, course_id, modules),
        pages_tab_off=pages_tab_off,
    )


def _read_files(
    canvas: CanvasClient, course_id: int, modules: list[Module]
) -> list[FileRef]:
    """The files modules hold that SurfSense can read. A file locked for the
    student has no link, and one of a type SurfSense refuses is never fetched."""
    files: list[FileRef] = []
    seen: set[int] = set()
    for module in modules:
        for item in module.items:
            file_id = item.get("content_id")
            if item.get("type") != "File" or not file_id or file_id in seen:
                continue
            seen.add(file_id)
            detail = canvas.get_one(f"/courses/{course_id}/files/{file_id}")
            name = detail.get("display_name") or ""
            if detail.get("url") and PurePosixPath(name).suffix.lower() in (
                SUPPORTED_UPLOAD_SUFFIXES
            ):
                files.append(
                    FileRef(
                        file_id,
                        name,
                        detail["url"],
                        module,
                        detail.get("size"),
                        detail.get("modified_at"),
                    )
                )
    return files


def read_modules(canvas: CanvasClient, course_id: int) -> list[Module]:
    raw = canvas.get_all(f"/courses/{course_id}/modules", {"include[]": "items"})
    return [
        Module(m["id"], number, m["name"], m.get("items", []))
        for number, m in enumerate(raw, start=1)
    ]


def read_file_refs(canvas: CanvasClient, course_id: int) -> list[FileRef]:
    """Only the files, for a check that fetches no bytes and writes nothing."""
    return _read_files(canvas, course_id, read_modules(canvas, course_id))


def _read_pages(
    canvas: CanvasClient, course_id: int, modules: list[Module]
) -> tuple[list[Page], bool]:
    """Every page: those the Pages tab lists, and those a module holds, and
    whether the tab was off.

    A course may turn its Pages tab off, which Canvas answers with a 404; the
    pages stay readable through the modules that hold them.
    """
    holder: dict[str, Module | None] = {}
    tab_off = False
    try:
        for entry in canvas.get_all(f"/courses/{course_id}/pages"):
            holder[entry["url"]] = None
    except CanvasNotFoundError:
        tab_off = True
    for module in modules:
        for item in module.items:
            slug = item.get("page_url")
            if item.get("type") == "Page" and slug and holder.get(slug) is None:
                holder[slug] = module

    pages = []
    for slug, module in holder.items():
        detail = canvas.get_one(f"/courses/{course_id}/pages/{quote(slug, safe='')}")
        pages.append(
            Page(
                page_id=detail["page_id"],
                slug=slug,
                title=detail.get("title") or slug,
                body=html_to_text(detail.get("body")),
                module=module,
            )
        )
    return pages, tab_off
