from sqlalchemy.orm import Session

from modules.canvas.sync.folders import ensure_folder
from modules.folders.models import Folder

# Link kind: the course's id stands for its folder of linked files.
ATTACHMENTS = "attachments_folder"
ATTACHMENTS_FOLDER = "Canvas files"


def ensure_attachments_folder(
    session: Session, workspace_id: int, course_id: int
) -> Folder:
    """Where files the course's text links to, and no module holds, are kept.

    Made only when there is such a file, and never renamed back: Canvas has no
    name for it, so the student's is the one to keep.
    """
    return ensure_folder(
        session,
        workspace_id,
        ATTACHMENTS,
        course_id,
        ATTACHMENTS_FOLDER,
        rename=False,
    )
