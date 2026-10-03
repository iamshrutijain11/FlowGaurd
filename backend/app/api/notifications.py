import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ERROR_RESPONSES, ApiResponse, ok
from app.schemas.notification import NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=ApiResponse[list[NotificationOut]],
    summary="List my notifications",
    description="Newest first. Poll this endpoint for near-real-time updates.",
    responses={401: ERROR_RESPONSES[401]},
)
def list_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = notification_service.list_notifications(db, user.id, unread_only)
    return ok([NotificationOut.model_validate(n) for n in items])


@router.patch(
    "/{notification_id}/read",
    response_model=ApiResponse[NotificationOut],
    summary="Mark a notification as read",
    description="Idempotent.",
    responses={401: ERROR_RESPONSES[401], 404: ERROR_RESPONSES[404]},
)
def mark_read(notification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = notification_service.mark_read(db, notification_id, user.id)
    return ok(NotificationOut.model_validate(n), "Notification marked as read")
