from dataclasses import dataclass

from modules.canvas.html_text import html_to_text
from modules.canvas.sync.assignment_ref import assignment_id_of, assignment_refs
from modules.canvas.sync.snapshot import CourseSnapshot, Module
from modules.canvas.sync.summaries import TITLE_PREFIX

# Link kind: a Canvas assignment's id stands for its note. The assignment's task
# is the separate `assignment` kind.
ASSIGNMENT_NOTE = "assignment_note"


@dataclass(frozen=True)
class AssignmentNote:
    assignment_id: int
    title: str
    content: str
    # The first module holding it; None for an assignment in none.
    module: Module | None


def build_assignment_notes(snapshot: CourseSnapshot) -> list[AssignmentNote]:
    """One note per assignment, so a lab can be ticked as a source and searched."""
    refs = assignment_refs(snapshot.assignments)
    holder: dict[int, Module] = {}
    for module in snapshot.modules:
        for item in module.items:
            assignment_id = assignment_id_of(item, refs)
            if assignment_id is not None and assignment_id not in holder:
                holder[assignment_id] = module
    return [
        AssignmentNote(
            assignment_id=a["id"],
            title=f"{TITLE_PREFIX}Assignment · {a.get('name')}",
            content=_content(a, snapshot.base_url),
            module=holder.get(a["id"]),
        )
        for a in snapshot.assignments
    ]


def _content(assignment: dict, base_url: str) -> str:
    due = (assignment.get("due_at") or "no due date")[:10]
    points = assignment.get("points_possible")
    shown = "?" if points is None else f"{points:g}"
    description = html_to_text(assignment.get("description"), base_url)
    head = f"# {assignment.get('name')}\n\nDue: {due}\nPoints: {shown}"
    return f"{head}\n\n{description}" if description else head
