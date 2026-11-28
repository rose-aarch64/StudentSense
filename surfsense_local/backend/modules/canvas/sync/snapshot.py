from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit

from modules.canvas.client import (
    CanvasClient,
    CanvasNotFoundError,
    CanvasUnreachableError,
)
from modules.canvas.html_text import html_to_text
from modules.canvas.sync.linked_files import linked_file_ids
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
    """A file a module holds, or that the course's text links to, with the signed
    link to fetch it by."""

    file_id: int
    name: str
    url: str
    # None for a file only the text links to.
    module: Module | None
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
    # The school's address, which the notes' relative links were made absolute with.
    base_url: str = ""
    # Linked files that could not be stored, by name (by id when Canvas gave none).
    skipped_files: list[str] = field(default_factory=list)


def read_course(canvas: CanvasClient, course_id: int) -> CourseSnapshot:
    course = canvas.get_one(f"/courses/{course_id}", {"include[]": "syllabus_body"})
    modules = read_modules(canvas, course_id)
    pages, pages_tab_off = _read_pages(canvas, course_id, modules)
    syllabus = html_to_text(course.get("syllabus_body"), canvas.origin)
    assignments = canvas.get_all(
        f"/courses/{course_id}/assignments", {"include[]": "submission"}
    )
    announcements = canvas.get_all(
        "/announcements", {"context_codes[]": f"course_{course_id}"}
    )
    module_files = _read_files(canvas, course_id, modules)
    texts = [
        syllabus,
        *(page.body for page in pages),
        *(a.get("description") or "" for a in assignments),
        *(a.get("message") or "" for a in announcements),
    ]
    linked, skipped = _read_linked_files(
        canvas,
        course_id,
        texts,
        announcements,
        {ref.file_id for ref in module_files},
    )
    return CourseSnapshot(
        syllabus=syllabus,
        assignments=assignments,
        announcements=announcements,
        modules=modules,
        pages=pages,
        files=[*module_files, *linked],
        pages_tab_off=pages_tab_off,
        base_url=canvas.origin,
        skipped_files=skipped,
    )


def _read_linked_files(
    canvas: CanvasClient,
    course_id: int,
    texts: list[str],
    announcements: list[dict],
    held_ids: set[int],
) -> tuple[list[FileRef], list[str]]:
    """The files the texts link to and the announcements attach, that no module
    holds, and the names of those that cannot be stored.

    A linked file Canvas refuses (locked, or for another section) is skipped, not
    fatal: the link in the note still goes to Canvas.
    """
    school_host = urlsplit(canvas.origin).netloc
    files: list[FileRef] = []
    skipped: list[str] = []
    seen = set(held_ids)
    for file_id in linked_file_ids(texts, course_id, school_host):
        if file_id in seen:
            continue
        seen.add(file_id)
        try:
            detail = canvas.get_one(f"/courses/{course_id}/files/{file_id}")
        except (CanvasNotFoundError, CanvasUnreachableError):
            skipped.append(str(file_id))
            continue
        _keep_or_skip(files, skipped, file_id, detail)
    for post in announcements:
        for attachment in post.get("attachments") or []:
            file_id = attachment.get("id")
            if file_id is None or file_id in seen:
                continue
            seen.add(file_id)
            _keep_or_skip(files, skipped, file_id, attachment)
    return files, skipped


def _keep_or_skip(
    files: list[FileRef], skipped: list[str], file_id: int, detail: dict
) -> None:
    name = detail.get("display_name") or ""
    if detail.get("url") and _is_readable(name):
        files.append(
            FileRef(
                file_id,
                name,
                detail["url"],
                None,
                detail.get("size"),
                detail.get("modified_at"),
            )
        )
    else:
        skipped.append(name or str(file_id))


def _is_readable(name: str) -> bool:
    return PurePosixPath(name).suffix.lower() in SUPPORTED_UPLOAD_SUFFIXES


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
                body=html_to_text(detail.get("body"), canvas.origin),
                module=module,
            )
        )
    return pages, tab_off
