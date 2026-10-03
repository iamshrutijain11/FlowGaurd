import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EventSource, EventType
from app.models.types import enum_type
from app.utils.time import utcnow


class GrievanceEvent(Base):
    """Immutable grievance history. Never update or delete rows."""

    __tablename__ = "grievance_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    grievance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grievances.id"), index=True)
    event_type: Mapped[EventType] = mapped_column(enum_type(EventType, "event_type"))
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[EventSource] = mapped_column(enum_type(EventSource, "event_source", 16))
    description: Mapped[str] = mapped_column(Text, default="")
    # DB column is "metadata" (API field name); attribute differs because `metadata` is reserved by SQLAlchemy.
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    grievance = relationship("Grievance", back_populates="events")
