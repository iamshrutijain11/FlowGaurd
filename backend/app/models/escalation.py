import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ActionType, EscalationStatus
from app.models.types import enum_type
from app.utils.time import utcnow


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    grievance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grievances.id"), index=True)
    escalation_type: Mapped[ActionType] = mapped_column(enum_type(ActionType, "action_type"))
    status: Mapped[EscalationStatus] = mapped_column(
        enum_type(EscalationStatus, "escalation_status", 16), default=EscalationStatus.PENDING
    )
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    guidance_source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
