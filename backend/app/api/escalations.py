import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ok
from app.schemas.grievance import NextActionOut
from app.services import grievance_service, next_action_service

router = APIRouter(prefix="/grievances", tags=["Next action"])


@router.get(
    "/{grievance_id}/next-action",
    response_model=ApiResponse[NextActionOut],
    summary="Recommended next step",
    description="Action category (NO_ACTION | FOLLOW_UP | REVIEW_DOCUMENTS | FURTHER_ACTION_AVAILABLE). Currently a placeholder provider; `official_source` stays null until verified guidance is wired in.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def next_action(grievance_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    return ok(next_action_service.get_next_action(db, g))
