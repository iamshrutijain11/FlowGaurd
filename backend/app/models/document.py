import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentType, ExtractionStatus
from app.models.types import enum_type
from app.utils.time import utcnow


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    grievance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grievances.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(String(500))  # relative to UPLOAD_DIR
    document_type: Mapped[DocumentType] = mapped_column(
        enum_type(DocumentType, "document_type"), default=DocumentType.OTHER
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        enum_type(ExtractionStatus, "extraction_status", 16), default=ExtractionStatus.PENDING
    )
    # AI suggestions only - never auto-applied to the grievance record.
    extracted_data_json: Mapped[dict[str, Any] | None] = mapped_column("extracted_data", JSON, nullable=True)

    grievance = relationship("Grievance", back_populates="documents")
