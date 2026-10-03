import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.guidance_loader import get_next_action_guidance
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import GrievanceStage
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ErrorResponse, ok
from app.schemas.grievance import GrievanceCreate, GrievanceOut, GrievanceUpdate, NextActionOut
from app.services import audit_service, grievance_service

router = APIRouter(prefix="/grievances", tags=["Grievances"])


@router.post(
    "",
    response_model=ApiResponse[GrievanceOut],
    status_code=201,
    summary="Create a grievance",
    description=(
        "Creates a grievance and its timeline events (FILED, plus ACKNOWLEDGED etc. if an acknowledgement "
        "date or later status is supplied). `complaint_id` must be unique per user."
    ),
    responses={409: {"model": ErrorResponse, "description": "DUPLICATE_COMPLAINT_ID"}, 401: ERROR_RESPONSES[401], 422: ERROR_RESPONSES[422]},
)
def create_grievance(body: GrievanceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.create_grievance(db, user, body)
    audit_service.log_action(db, user_id=user.id, action="GRIEVANCE_CREATED", resource_type="grievance", resource_id=g.id)
    return ok(grievance_service.grievance_out(g), "Grievance created")


@router.get(
    "",
    response_model=ApiResponse[list[GrievanceOut]],
    summary="List my grievances",
    description="All grievances of the current user, most recently updated first. Each item includes the active FlowGuard `warning` (if any), kept separate from `current_stage`.",
    responses={401: ERROR_RESPONSES[401]},
)
def list_grievances(
    stage: GrievanceStage | None = Query(default=None, description="Filter by stage"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = [grievance_service.grievance_out(g) for g in grievance_service.list_grievances(db, user, stage)]
    return ok(items)


@router.get(
    "/{grievance_id}",
    response_model=ApiResponse[GrievanceOut],
    summary="Get a grievance",
    description="Returns one grievance owned by the current user.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def get_grievance(grievance_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    return ok(grievance_service.grievance_out(g))


@router.patch(
    "/{grievance_id}",
    response_model=ApiResponse[GrievanceOut],
    summary="Update a grievance",
    description=(
        "Partial update. A `current_stage` change appends a timeline event and creates a notification; "
        "detail edits append a DETAILS_UPDATED event (history is never silently altered). "
        "Transitions are validated by the workflow state machine once it is merged."
    ),
    responses={409: {"model": ErrorResponse, "description": "INVALID_STAGE_TRANSITION"}, 401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404], 422: ERROR_RESPONSES[422]},
)
def update_grievance(
    grievance_id: uuid.UUID, body: GrievanceUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    g = grievance_service.update_grievance(db, g, body)
    audit_service.log_action(
        db, user_id=user.id, action="GRIEVANCE_UPDATED", resource_type="grievance", resource_id=g.id,
        metadata={"fields": list(body.model_dump(exclude_unset=True).keys())},
    )
    return ok(grievance_service.grievance_out(g), "Grievance updated")


@router.get(
    "/{grievance_id}/next-action",
    response_model=ApiResponse[NextActionOut],
    summary="Recommended next step",
    description="Action category and verified next-action guidance from FlowGuard regulatory catalogs.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def next_action(grievance_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    return ok(get_next_action_guidance(db, g))
