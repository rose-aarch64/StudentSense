from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.canvas.models import CanvasLink

COURSE = "course"
TERM = "term"


def linked_id(session: Session, kind: str, canvas_id: int) -> int | None:
    """The local id a Canvas item became, or None if it has none yet."""
    return session.scalar(
        select(CanvasLink.local_id).where(
            CanvasLink.kind == kind, CanvasLink.canvas_id == canvas_id
        )
    )


def linked_ids(session: Session, kind: str) -> set[int]:
    return set(
        session.scalars(select(CanvasLink.local_id).where(CanvasLink.kind == kind))
    )


def remember(session: Session, kind: str, canvas_id: int, local_id: int) -> None:
    """Link a Canvas item to its local one, replacing a stale link."""
    link = session.scalar(
        select(CanvasLink).where(
            CanvasLink.kind == kind, CanvasLink.canvas_id == canvas_id
        )
    )
    if link is None:
        session.add(CanvasLink(kind=kind, canvas_id=canvas_id, local_id=local_id))
    else:
        link.local_id = local_id
