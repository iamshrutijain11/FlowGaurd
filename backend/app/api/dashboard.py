from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ok
from app.schemas.grievance import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=ApiResponse[DashboardSummary],
    summary="Dashboard counts",
    description="`active` = not RESOLVED; `potentially_delayed` = active with a POTENTIAL_DELAY warning; `on_track` = active - potentially_delayed.",
    responses={401: ERROR_RESPONSES[401]},
)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ok(dashboard_service.get_summary(db, user))
