import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.config import settings
from app.models.enums import DocumentType, ExtractionStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    grievance_id: uuid.UUID
    file_name: str
    file_type: str
    document_type: DocumentType
    uploaded_at: datetime
    extraction_status: ExtractionStatus
    # AI-extracted SUGGESTIONS (unconfirmed). Null until Person 4's extraction runs.
    extracted_data: dict[str, Any] | None = None
    download_url: str


def document_out(d) -> DocumentOut:
    return DocumentOut(
        id=d.id,
        grievance_id=d.grievance_id,
        file_name=d.file_name,
        file_type=d.file_type,
        document_type=d.document_type,
        uploaded_at=d.uploaded_at,
        extraction_status=d.extraction_status,
        extracted_data=d.extracted_data_json,
        download_url=f"{settings.API_V1_PREFIX}/documents/{d.id}/download",
    )
