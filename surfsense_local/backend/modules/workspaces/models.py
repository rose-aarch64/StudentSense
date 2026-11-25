from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db import Base

if TYPE_CHECKING:
    from modules.chat.models import ChatThread
    from modules.documents.models import Document


class WorkspaceFolder(Base):
    """A named group of workspaces. Deleting one unfiles them, never deletes them."""

    __tablename__ = "workspace_folders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    # A key into the interface's icon set; unknown keys show the initials.
    icon: Mapped[str | None]
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspace_folders.id", ondelete="SET NULL")
    )
    # The hosted workspace this one was imported from, so a re-import finds it.
    cloud_id: Mapped[int | None] = mapped_column(unique=True)
    # Protect history imported before chat threads kept their hosted ids.
    has_unkeyed_imported_threads: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", passive_deletes=True
    )
    chat_threads: Mapped[list["ChatThread"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", passive_deletes=True
    )
