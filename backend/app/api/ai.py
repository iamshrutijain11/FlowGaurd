import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ok
from app.schemas.grievance import ExplanationOut
from app.services import explanation_service, grievance_service

router = APIRouter(prefix="/grievances", tags=["AI"])


@router.get(
    "/{grievance_id}/explanation",
    response_model=ApiResponse[ExplanationOut],
    summary="Plain-language explanation",
    description="Currently template text (`is_placeholder: true`); the AI layer replaces the provider in `services/explanation_service.py` without changing this response shape.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def explanation(grievance_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    return ok(explanation_service.get_explanation(db, g))
