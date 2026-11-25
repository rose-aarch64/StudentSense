import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base, text_enum


class TodoSource(enum.Enum):
    MANUAL = "manual"
    CANVAS = "canvas"


class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = (
        # How a sync finds the task it made; NULL keys, the manual tasks, may repeat.
        UniqueConstraint("source", "source_key"),
        Index("todos_workspace", "workspace_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # A task about no class has none; deleting a workspace deletes its tasks.
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    title: Mapped[str]
    due_at: Mapped[datetime | None]
    done_at: Mapped[datetime | None]
    source: Mapped[TodoSource] = mapped_column(
        text_enum(TodoSource), server_default=TodoSource.MANUAL.value
    )
    source_key: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
