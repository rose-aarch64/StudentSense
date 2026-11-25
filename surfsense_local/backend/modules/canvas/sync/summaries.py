from dataclasses import dataclass

from modules.canvas.html_text import html_to_text
from modules.canvas.sync.snapshot import CourseSnapshot

TITLE_PREFIX = "Canvas · "


@dataclass(frozen=True)
class Summary:
    """A note about a whole course, found again by the course's id and its kind."""

    kind: str
    title: str
    content: str


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
            "\n\n".join(_announcement_block(a) for a in snapshot.announcements),
        ),
        (
            "modules_note",
            "Modules",
            "\n\n".join(_module_block(m) for m in snapshot.modules),
        ),
    ]
    return [
        Summary(kind, f"{TITLE_PREFIX}{name}", f"# {name}\n\n{body}")
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


def _announcement_block(post: dict) -> str:
    posted = (post.get("posted_at") or "")[:10]
    return f"## {post.get('title')} ({posted})\n{html_to_text(post.get('message'))}"


def _module_block(module) -> str:
    items = "\n".join(f"- {i.get('title')} ({i.get('type')})" for i in module.items)
    return f"## {module.name}\n{items}"
