import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import NotificationType
from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    grievance_id: uuid.UUID | None,
    notification_type: NotificationType,
    title: str,
    message: str,
    commit: bool = True,
) -> Notification:
    n = Notification(
        user_id=user_id,
        grievance_id=grievance_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )
    db.add(n)
    db.commit() if commit else db.flush()
    return n


def list_notifications(db: Session, user_id: uuid.UUID, unread_only: bool = False) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.read.is_(False))
    return list(db.scalars(q.order_by(Notification.created_at.desc())))


def mark_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user_id:
        raise AppError("NOTIFICATION_NOT_FOUND", "Notification not found", 404)
    n.read = True
    db.commit()
    return n
