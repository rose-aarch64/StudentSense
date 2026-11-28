from modules.canvas.sync.assignment_ref import assignment_id_of, assignment_refs
from modules.canvas.sync.snapshot import CourseSnapshot

# Where the Modules note keeps the course's ordered items, in its metadata.
OUTLINE_KEY = "canvas_modules"


def build_outline(snapshot: CourseSnapshot) -> list[dict]:
    """Each module's items in Canvas's order, headers and links included.

    Items are named by Canvas ids, not local ones: a file not yet fetched has no
    document, and the view looks the rows up when it is asked for.
    """
    page_ids = {page.slug: page.page_id for page in snapshot.pages}
    assignments = {a["id"]: a for a in snapshot.assignments}
    refs = assignment_refs(snapshot.assignments)
    return [
        {
            "id": module.id,
            "name": module.name,
            "items": [_item(i, page_ids, assignments, refs) for i in module.items],
        }
        for module in snapshot.modules
    ]


def _item(
    item: dict,
    page_ids: dict[str, int],
    assignments: dict[int, dict],
    refs: dict[tuple[str, int], int],
) -> dict:
    kind = item.get("type")
    canvas_id = None
    due_at = points = None
    if kind == "Page":
        canvas_id = page_ids.get(item.get("page_url"))
    elif kind == "File":
        canvas_id = item.get("content_id")
    else:
        canvas_id = assignment_id_of(item, refs)
    if canvas_id is not None and kind not in ("Page", "File"):
        assignment = assignments.get(canvas_id) or {}
        due_at = assignment.get("due_at")
        points = assignment.get("points_possible")
    return {
        "type": kind,
        "title": item.get("title"),
        "canvas_id": canvas_id,
        "url": item.get("external_url"),
        "due_at": due_at,
        "points": points,
    }
