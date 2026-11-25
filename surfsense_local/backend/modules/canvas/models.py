from datetime import datetime

from sqlalchemy import CheckConstraint, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class CanvasConnection(Base):
    """One row: the school's Canvas and the access token that reads it."""

    __tablename__ = "canvas_connection"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    base_url: Mapped[str]
    # Encrypted with the install's secret, like a provider's key.
    token_ciphertext: Mapped[bytes]
    # Who Canvas says the token belongs to, shown so a wrong account is noticed.
    user_name: Mapped[str | None]
    # Off until the user turns it on: the refresh uses the token with nobody there.
    auto_refresh: Mapped[bool] = mapped_column(server_default=false())
    # When the last refresh pass succeeded, and the code of how the last one failed.
    refreshed_at: Mapped[datetime | None]
    refresh_error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class CanvasLink(Base):
    """Which SurfSense item a Canvas item became, so a sync finds it by id.

    A course points at a workspace, a module at a folder, a page or file at a
    document, an assignment at a task. `kind` is plain text, not an enum, so a
    new kind needs no table rebuild. A link to an item the user deleted is
    stale, and the sync makes the item again.
    """

    __tablename__ = "canvas_links"
    __table_args__ = (UniqueConstraint("kind", "canvas_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str]
    canvas_id: Mapped[int]
    local_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
