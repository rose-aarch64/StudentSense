from dataclasses import dataclass

from modules.canvas.html_text import html_to_text
from modules.canvas.sync.outline import OUTLINE_KEY, build_outline
from modules.canvas.sync.snapshot import CourseSnapshot

TITLE_PREFIX = "Canvas · "
# Link kind of the summary note that also keeps the course's outline.
MODULES_NOTE = "modules_note"


@dataclass(frozen=True)
class Summary:
    """A note about a whole course, found again by the course's id and its kind."""

    kind: str
    title: str
    content: str
    # Saved with the note and left alone by edits to its text.
    metadata: dict | None = None


def build_summaries(snapshot: CourseSnapshot) -> list[Summary]:
    """One note each for the syllabus, assignments, announcements and modules,
    leaving out any with nothing in it."""
    sections = [
        ("syllabus_note", "Syllabus", snapshot.syllabus.strip()),
        (
            "assignments_note",
            "Assignments",
            "\n".join(_assignment_line(a) for a in snapshot.assignments),
        ),
        (
            "announcements_note",
            "Announcements",
            "\n\n".join(
                _announcement_block(a, snapshot.base_url)
                for a in snapshot.announcements
            ),
        ),
        (
            MODULES_NOTE,
            "Modules",
            "\n\n".join(_module_block(m) for m in snapshot.modules),
        ),
        (
            "links_note",
            "Links",
            "\n\n".join(block for m in snapshot.modules if (block := _links_block(m))),
        ),
    ]
    outline = {OUTLINE_KEY: build_outline(snapshot)}
    return [
        Summary(
            kind,
            f"{TITLE_PREFIX}{name}",
            f"# {name}\n\n{body}",
            metadata=outline if kind == MODULES_NOTE else None,
        )
        for kind, name, body in sections
        if body
    ]


def _assignment_line(assignment: dict) -> str:
    due = (assignment.get("due_at") or "no due date")[:10]
    points = assignment.get("points_possible")
    submission = assignment.get("submission") or {}
    state = submission.get("workflow_state") or "not submitted"
    shown = points if points is not None else "?"
    return f"- {assignment.get('name')} | due {due} | {shown} pts | {state}"


def _announcement_block(post: dict, base_url: str) -> str:
    posted = (post.get("posted_at") or "")[:10]
    message = html_to_text(post.get("message"), base_url)
    return f"## {post.get('title')} ({posted})\n{message}"


def _links_block(module) -> str:
    """A module's external links with their addresses; empty when it has none."""
    lines = [
        f"- [{i.get('title')}]({i['external_url']})"
        for i in module.items
        if i.get("external_url")
    ]
    return f"## {module.name}\n" + "\n".join(lines) if lines else ""


def _module_block(module) -> str:
    items = "\n".join(f"- {i.get('title')} ({i.get('type')})" for i in module.items)
    return f"## {module.name}\n{items}"
