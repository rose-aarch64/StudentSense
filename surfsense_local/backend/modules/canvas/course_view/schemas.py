from pydantic import BaseModel


class ItemView(BaseModel):
    """One thing a module holds, in Canvas's order."""

    type: str
    title: str
    # The source it became, when it became one: a page, a file or an assignment.
    document_id: int | None = None
    # Where a link goes.
    url: str | None = None
    due_at: str | None = None
    points: float | None = None


class ModuleView(BaseModel):
    id: int
    name: str
    # The folder holding the module's sources; None when it holds none.
    folder_id: int | None
    items: list[ItemView]


class CourseView(BaseModel):
    """A synced class laid out as Canvas lays out its Modules page."""

    # False for a workspace Canvas did not make, and for a class synced before
    # the outline was kept.
    synced: bool
    # A Canvas class with no outline yet: one sync makes it.
    needs_sync: bool = False
    textbook_folder_id: int | None = None
    # The Overview notes by name: syllabus, announcements, assignments, links.
    notes: dict[str, int] = {}
    # Canvas file id -> the source it became, for the links in the class's notes.
    files: dict[int, int] = {}
    modules: list[ModuleView] = []
