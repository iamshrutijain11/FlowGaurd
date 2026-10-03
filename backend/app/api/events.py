import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.enums import USER_ALLOWED_EVENT_TYPES, EventSource
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ok
from app.schemas.event import EventCreate, EventOut, event_out
from app.services import event_service, grievance_service

router = APIRouter(prefix="/grievances", tags=["Events"])


@router.get(
    "/{grievance_id}/events",
    response_model=ApiResponse[list[EventOut]],
    summary="Grievance timeline",
    description="Chronological, append-only event history. Warning events have source SYSTEM and carry `rule_id`, `reason` and `based_on_event` in `metadata`.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def list_events(grievance_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    return ok([event_out(e) for e in event_service.list_events(db, g.id)])


@router.post(
    "/{grievance_id}/events",
    response_model=ApiResponse[EventOut],
    status_code=201,
    summary="Add a timeline entry",
    description="Investors may add NOTE_ADDED or FOLLOW_UP_SENT entries (source is always USER). Stage changes use PATCH /grievances/{id}; warnings are created by the workflow engine. Events cannot be edited or deleted.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404], 422: ERROR_RESPONSES[422]},
)
def add_event(
    grievance_id: str, body: EventCreate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    g = grievance_service.get_owned_grievance(db, grievance_id, user)
    if body.event_type not in USER_ALLOWED_EVENT_TYPES:
        raise AppError(
            "EVENT_TYPE_NOT_ALLOWED",
            "Only NOTE_ADDED and FOLLOW_UP_SENT can be added manually. Use PATCH to change the stage.",
            422,
        )
    e = event_service.create_event(
        db, g.id, body.event_type, body.description,
        source=EventSource.USER, event_time=body.event_time, metadata=body.metadata,
    )
    return ok(event_out(e), "Event recorded")
