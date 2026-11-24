
import uuid

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    JSON,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    provider_call_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )

    phone_number: Mapped[str] = mapped_column(String(20))

    direction: Mapped[str] = mapped_column(
        String(20),
        default="outbound",
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="initiated",
    )

    outcome: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    events: Mapped[list["CallEvent"]] = relationship(
        back_populates="call",
        cascade="all, delete-orphan",
    )


class CallEvent(Base):
    __tablename__ = "call_events"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(100))

    payload: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    call: Mapped["Call"] = relationship(
        back_populates="events",
    )
