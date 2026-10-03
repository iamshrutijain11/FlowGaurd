import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import GrievanceStage
from app.models.types import enum_type
from app.utils.time import utcnow


class Grievance(Base):
    __tablename__ = "grievances"
    __table_args__ = (UniqueConstraint("user_id", "complaint_id", name="uq_grievance_user_complaint"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    complaint_id: Mapped[str] = mapped_column(String(100))
    entity_name: Mapped[str] = mapped_column(String(255))
    issue_type: Mapped[str] = mapped_column(String(255))
    issue_description: Mapped[str] = mapped_column(Text, default="", server_default="")
    submission_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_stage: Mapped[GrievanceStage] = mapped_column(
        enum_type(GrievanceStage, "grievance_stage"), default=GrievanceStage.FILED, index=True
    )
    status_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )

    user = relationship("User", back_populates="grievances")
    # Events are the immutable timeline: no delete cascade, ordered chronologically.
    events = relationship(
        "GrievanceEvent",
        back_populates="grievance",
        order_by="GrievanceEvent.event_time",
    )
    documents = relationship("Document", back_populates="grievance", order_by="Document.uploaded_at")
