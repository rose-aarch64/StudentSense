from sqlalchemy.orm import Session

from modules.canvas.sync.folders import ensure_folder
from modules.folders.models import Folder

# Link kind: the course's id stands for its Textbook folder.
TEXTBOOK = "textbook_folder"
TEXTBOOK_FOLDER = "Textbook"


def ensure_textbook_folder(
    session: Session, workspace_id: int, course_id: int
) -> Folder:
    """Where the student imports the class's book. The sync makes the folder and
    never writes into it, so an imported book stays through every sync. Canvas
    does not name the folder, so a name the student gave it is kept."""
    return ensure_folder(
        session, workspace_id, TEXTBOOK, course_id, TEXTBOOK_FOLDER, rename=False
    )
