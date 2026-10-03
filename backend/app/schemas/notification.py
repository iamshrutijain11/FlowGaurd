import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    grievance_id: uuid.UUID | None = None
    notification_type: NotificationType
    title: str
    message: str
    read: bool
    created_at: datetime
