"""
app.notifications - FlowGuard Notification Service Package.
"""

from app.notifications.notifications import (
    NotificationType,
    NotificationSeverity,
    NotificationChannel,
    NotificationItem,
    NotificationService,
    notification_service,
    create_stage_transition_notification,
    create_delay_warning_notification,
    create_evidence_reminder_notification,
    create_next_action_notification,
    format_email_demo,
    format_sms_demo,
    get_demo_notifications,
)

__all__ = [
    "NotificationType",
    "NotificationSeverity",
    "NotificationChannel",
    "NotificationItem",
    "NotificationService",
    "notification_service",
    "create_stage_transition_notification",
    "create_delay_warning_notification",
    "create_evidence_reminder_notification",
    "create_next_action_notification",
    "format_email_demo",
    "format_sms_demo",
    "get_demo_notifications",
]
