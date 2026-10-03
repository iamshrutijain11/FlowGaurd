import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.document import Document
from app.models.enums import DocumentType, EventSource, EventType, ExtractionStatus
from app.models.grievance import Grievance
from app.models.user import User
from app.services import event_service

# extension -> (mime type, magic-byte prefixes)
_ALLOWED = {
    ".pdf": ("application/pdf", (b"%PDF",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
}


def upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_document(
    db: Session, grievance: Grievance, user: User, upload: UploadFile, document_type: DocumentType
) -> Document:
    original = Path(upload.filename or "upload").name  # strip any path components
    ext = Path(original).suffix.lower()
    if ext not in _ALLOWED:
        raise AppError("UNSUPPORTED_FILE_TYPE", "Only PDF, PNG and JPG/JPEG files are supported.", 415)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    content = upload.file.read(max_bytes + 1)
    if not content:
        raise AppError("EMPTY_FILE", "The uploaded file is empty.", 400)
    if len(content) > max_bytes:
        raise AppError("FILE_TOO_LARGE", f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit.", 413)

    mime, magics = _ALLOWED[ext]
    if not content.startswith(magics):  # content must match the extension
        raise AppError("UNSUPPORTED_FILE_TYPE", "File content does not match its extension.", 415)

    rel = Path(str(grievance.id)) / f"{uuid.uuid4()}{ext}"
    target = upload_root() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    doc = Document(
        grievance_id=grievance.id,
        file_name=original[:255],
        file_type=mime,
        storage_path=rel.as_posix(),
        document_type=document_type,
        extraction_status=ExtractionStatus.PENDING,  # Person 4's AI layer picks these up
    )
    db.add(doc)
    db.flush()
    event_service.create_event(
        db,
        grievance.id,
        EventType.DOCUMENT_UPLOADED,
        f"Document uploaded: {original} ({document_type.value.replace('_', ' ').title()}).",
        source=EventSource.USER,
        metadata={"document_id": str(doc.id), "document_type": document_type.value},
        commit=False,
    )
    db.commit()
    return doc


def list_documents(grievance: Grievance) -> list[Document]:
    return list(grievance.documents)


def get_owned_document(db: Session, document_id: uuid.UUID, user: User) -> Document:
    doc = db.get(Document, document_id)
    if not doc or doc.grievance.user_id != user.id:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", 404)
    return doc


def update_extraction_result(
    db: Session, document_id: uuid.UUID, *, status: ExtractionStatus, data: dict | None = None
) -> Document:
    """For Person 4: store AI extraction output. Values are SUGGESTIONS; grievance fields
    are never overwritten automatically."""
    doc = db.get(Document, document_id)
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", 404)
    doc.extraction_status = status
    if data is not None:
        doc.extracted_data_json = data
    db.commit()
    return doc
