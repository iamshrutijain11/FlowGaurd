import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.enums import DocumentType
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ErrorResponse, ok
from app.schemas.document import DocumentOut, document_out
from app.services import audit_service, document_service, grievance_service

router = APIRouter(tags=["Documents"])

_UPLOAD_ERRORS = {
    400: {"model": ErrorResponse, "description": "EMPTY_FILE"},
    413: {"model": ErrorResponse, "description": "FILE_TOO_LARGE"},
    415: {"model": ErrorResponse, "description": "UNSUPPORTED_FILE_TYPE"},
    401: ERROR_RESPONSES[401],
    404: ERROR_RESPONSES[404],
}


@router.post(
    "/grievances/{grievance_id}/documents",
    response_model=ApiResponse[DocumentOut],
    status_code=201,
    summary="Upload a document",
    description="multipart/form-data: `file` (PDF/PNG/JPG/JPEG, max size from MAX_UPLOAD_MB) and `document_type`. The file is stored on disk, `extraction_status` starts as PENDING for the AI layer, and a DOCUMENT_UPLOADED event is added to the timeline.",
    responses=_UPLOAD_ERRORS,
)
def upload_document(
    grievance_id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    doc = document_service.save_document(db, g, user, file, document_type)
    audit_service.log_action(
        db, user_id=user.id, action="DOCUMENT_UPLOADED", resource_type="document", resource_id=doc.id,
        metadata={"grievance_id": str(g.id), "document_type": document_type.value},
    )
    return ok(document_out(doc), "Document uploaded")


@router.get(
    "/grievances/{grievance_id}/documents",
    response_model=ApiResponse[list[DocumentOut]],
    summary="List documents of a grievance",
    description="Includes `extraction_status` and (once available) AI-extracted `extracted_data`, which are unconfirmed suggestions.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def list_documents(grievance_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    return ok([document_out(d) for d in document_service.list_documents(g)])


@router.get(
    "/documents/{document_id}",
    response_model=ApiResponse[DocumentOut],
    summary="Get document metadata",
    description="Metadata only; use `download_url` for the file.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ok(document_out(document_service.get_owned_document(db, document_id, user)))


@router.get(
    "/documents/{document_id}/download",
    summary="Download a document file",
    description="Streams the stored file. Requires the Authorization header, so fetch it with the JWT (e.g. as a blob) rather than a plain <a href>.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def download_document(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = document_service.get_owned_document(db, document_id, user)
    path = document_service.upload_root() / doc.storage_path
    if not path.is_file():
        raise AppError("FILE_MISSING", "The stored file could not be found.", 404)
    return FileResponse(path, media_type=doc.file_type, filename=doc.file_name)
