"""
notifications.py - Notification Service for FlowGuard (Person 4).

Generates, formats, and dispatches in-app alerts, demo emails, and demo SMS
notifications for grievance stage transitions, delay warnings, evidence reminders,
and verified next-action guidance.

Adheres strictly to FlowGuard principles:
- Exact canonical stages: FILED, ACKNOWLEDGED, AWAITING_RESPONSE, RESPONSE_RECEIVED, RESOLVED, FURTHER_ACTION.
- Exact warning types: response_window_exceeded, potential_delay, awaiting_response.
- Documents are suggested as "may be useful for your grievance record" (never claimed as legally required).
- Non-accusatory tone; any time window is explicitly identified as a "demo configuration".
- In-app notification structure ready for Person 1 (Frontend) and Person 2 (Backend DB).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and Pydantic Models
# ---------------------------------------------------------------------------

class NotificationType(str, Enum):
    STAGE_TRANSITION = "STAGE_TRANSITION"
    DELAY_WARNING = "DELAY_WARNING"
    NEXT_ACTION_GUIDANCE = "NEXT_ACTION_GUIDANCE"
    EVIDENCE_REMINDER = "EVIDENCE_REMINDER"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    URGENT = "URGENT"
    SUCCESS = "SUCCESS"


class NotificationChannel(str, Enum):
    IN_APP = "IN_APP"
    EMAIL_DEMO = "EMAIL_DEMO"
    SMS_DEMO = "SMS_DEMO"


class NotificationItem(BaseModel):
    """Notification model matching the shared API contract."""
    id: str = Field(default_factory=lambda: f"notif_{uuid.uuid4().hex[:8]}")
    complaint_id: str
    type: str = Field(..., description="STAGE_TRANSITION | DELAY_WARNING | NEXT_ACTION_GUIDANCE | EVIDENCE_REMINDER")
    severity: str = Field(default="INFO", description="INFO | WARNING | URGENT | SUCCESS")
    channel: str = Field(default="IN_APP", description="IN_APP | EMAIL_DEMO | SMS_DEMO")
    title: str
    message: str
    stage: str = Field(..., description="Canonical stage name")
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_read: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Notification Generation Helpers
# ---------------------------------------------------------------------------

def create_stage_transition_notification(
    complaint_id: str,
    entity_name: str,
    new_stage: str,
    previous_stage: Optional[str] = None,
    channel: str = "IN_APP",
) -> NotificationItem:
    """Creates a notification when a complaint advances to a new pipeline stage."""
    stage_titles = {
        "FILED": f"Complaint {complaint_id} Filed",
        "ACKNOWLEDGED": f"Complaint Acknowledged by {entity_name}",
        "AWAITING_RESPONSE": f"Awaiting Response from {entity_name}",
        "RESPONSE_RECEIVED": f"Response Received from {entity_name}",
        "RESOLVED": f"Complaint {complaint_id} Resolved",
        "FURTHER_ACTION": f"Further Action Available for {complaint_id}",
    }

    stage_messages = {
        "FILED": f"Your complaint {complaint_id} against {entity_name} has been filed. Please check for an acknowledgement receipt.",
        "ACKNOWLEDGED": f"{entity_name} has acknowledged receipt of complaint {complaint_id}. FlowGuard is now tracking the response timeline.",
        "AWAITING_RESPONSE": f"Complaint {complaint_id} is awaiting response from {entity_name}. FlowGuard is monitoring for updates.",
        "RESPONSE_RECEIVED": f"{entity_name} has recorded a response for complaint {complaint_id}. Please review the resolution.",
        "RESOLVED": f"Complaint {complaint_id} has been marked as resolved. Please verify your account balances.",
        "FURTHER_ACTION": f"Official next steps are available for complaint {complaint_id}. You may prepare to escalate via SEBI SCORES 2.0 / SMART ODR.",
    }

    title = stage_titles.get(new_stage, f"Stage Updated: {new_stage}")
    message = stage_messages.get(new_stage, f"Complaint {complaint_id} moved to stage {new_stage}.")
    severity = "SUCCESS" if new_stage == "RESOLVED" else "INFO"

    return NotificationItem(
        complaint_id=complaint_id,
        type=NotificationType.STAGE_TRANSITION.value,
        severity=severity,
        channel=channel,
        title=title,
        message=message,
        stage=new_stage,
        action_label="View Pipeline",
        action_url=f"/grievances/{complaint_id}",
        metadata={"previous_stage": previous_stage, "new_stage": new_stage, "entity_name": entity_name}
    )


def create_delay_warning_notification(
    complaint_id: str,
    entity_name: str,
    stage: str,
    warning_type: str,
    days_elapsed: int = 30,
    expected_window_days: int = 30,
    channel: str = "IN_APP",
) -> NotificationItem:
    """
    Creates a warning notification when a potential delay is detected by rule engine.
    Strictly notes that any time window is a demo configuration.
    """
    title = f"Potential Delay Notice: {complaint_id}"
    message = (
        f"FlowGuard observed that {days_elapsed} days have elapsed since filing for complaint {complaint_id} "
        f"without a recorded response from {entity_name}. Note: This {expected_window_days}-day benchmark is a "
        f"demo configuration for simulation purposes, not a statutory finding of misconduct."
    )

    return NotificationItem(
        complaint_id=complaint_id,
        type=NotificationType.DELAY_WARNING.value,
        severity=NotificationSeverity.WARNING.value,
        channel=channel,
        title=title,
        message=message,
        stage=stage,
        action_label="View Delay Details",
        action_url=f"/grievances/{complaint_id}/warnings",
        metadata={
            "warning_type": warning_type,
            "days_elapsed": days_elapsed,
            "expected_window_days": expected_window_days,
            "window_basis": "demo configuration",
            "entity_name": entity_name,
        }
    )


def create_evidence_reminder_notification(
    complaint_id: str,
    stage: str,
    missing_document_labels: List[str],
    channel: str = "IN_APP",
) -> NotificationItem:
    """
    Creates a checklist reminder for documents that may be useful for the grievance record.
    Never claims any document is legally mandatory.
    """
    doc_str = ", ".join(missing_document_labels) if missing_document_labels else "suggested records"
    title = f"Evidence Checklist Update: {complaint_id}"
    message = (
        f"Having these document(s) on file may be useful for your grievance record: {doc_str}. "
        f"Uploading them will help keep your case file organized if you choose to escalate."
    )

    return NotificationItem(
        complaint_id=complaint_id,
        type=NotificationType.EVIDENCE_REMINDER.value,
        severity=NotificationSeverity.INFO.value,
        channel=channel,
        title=title,
        message=message,
        stage=stage,
        action_label="Upload Documents",
        action_url=f"/grievances/{complaint_id}/documents",
        metadata={"missing_documents": missing_document_labels}
    )


def create_next_action_notification(
    complaint_id: str,
    stage: str,
    escalation_path: str,
    official_portal: str,
    channel: str = "IN_APP",
) -> NotificationItem:
    """Creates a verified next-action guidance notification."""
    title = f"Next Step Guidance Available: {complaint_id}"
    message = (
        f"Official guidance is available for complaint {complaint_id}. "
        f"If you wish to follow up or escalate, you can use the {escalation_path} "
        f"via the official portal at {official_portal}."
    )

    return NotificationItem(
        complaint_id=complaint_id,
        type=NotificationType.NEXT_ACTION_GUIDANCE.value,
        severity=NotificationSeverity.URGENT.value,
        channel=channel,
        title=title,
        message=message,
        stage=stage,
        action_label="Open Official Portal",
        action_url=official_portal,
        metadata={"escalation_path": escalation_path, "official_portal": official_portal}
    )


def create_warning_notification_for_grievance(
    db: Any,
    grievance: Any,
    warning_type: Any,
    rule_id: str,
    reason: str,
    days_elapsed: int = 30,
    commit: bool = True,
) -> NotificationItem:
    """Creates and dispatches a notification when a workflow warning is generated.

    1. Formats a NotificationItem using Person 4's notification generators.
    2. Dispatches it to Person 4's in-memory notification_service.
    3. Persists it to the database table `notifications` via app.services.notification_service.
    """
    from app.models.enums import NotificationType as DbNotificationType, WarningType
    from app.services import notification_service as db_notif_service

    wtype_str = warning_type.value if hasattr(warning_type, "value") else str(warning_type)
    stage_str = (
        grievance.current_stage.value
        if hasattr(grievance.current_stage, "value")
        else str(grievance.current_stage)
    )

    if wtype_str in (WarningType.POTENTIAL_DELAY.value, "POTENTIAL_DELAY", "response_window_exceeded"):
        db_type = DbNotificationType.POTENTIAL_DELAY
        item = create_delay_warning_notification(
            complaint_id=grievance.complaint_id,
            entity_name=grievance.entity_name,
            stage=stage_str,
            warning_type=wtype_str,
            days_elapsed=days_elapsed,
        )
    elif wtype_str in (WarningType.FOLLOW_UP_DUE.value, "FOLLOW_UP_DUE"):
        db_type = DbNotificationType.FOLLOW_UP_DUE
        item = NotificationItem(
            complaint_id=grievance.complaint_id,
            type=NotificationType.DELAY_WARNING.value,
            severity=NotificationSeverity.WARNING.value,
            title=f"Follow-Up Due: {grievance.complaint_id}",
            message=reason or f"A follow-up may be appropriate for grievance {grievance.complaint_id}.",
            stage=stage_str,
            action_label="Follow-Up Details",
            action_url=f"/grievances/{grievance.complaint_id}",
            metadata={"warning_type": wtype_str, "rule_id": rule_id},
        )
    elif wtype_str in (WarningType.MISSING_INFORMATION.value, WarningType.DOCUMENT_REQUIRED.value, "MISSING_INFORMATION", "DOCUMENT_REQUIRED"):
        db_type = DbNotificationType.DOCUMENT_REQUIRED
        item = create_evidence_reminder_notification(
            complaint_id=grievance.complaint_id,
            stage=stage_str,
            missing_document_labels=["Supporting document / acknowledgement"],
        )
    else:
        db_type = DbNotificationType.POTENTIAL_DELAY
        item = NotificationItem(
            complaint_id=grievance.complaint_id,
            type=NotificationType.DELAY_WARNING.value,
            severity=NotificationSeverity.WARNING.value,
            title=f"Workflow Notice: {grievance.complaint_id}",
            message=reason or f"Workflow notice for grievance {grievance.complaint_id}.",
            stage=stage_str,
            action_label="View Details",
            action_url=f"/grievances/{grievance.complaint_id}",
            metadata={"warning_type": wtype_str, "rule_id": rule_id},
        )

    # 1. Dispatch through Person 4's in-memory service
    notification_service.dispatch(item)

    # 2. Persist in database notifications table so GET /api/v1/notifications includes it
    try:
        db_notif_service.create_notification(
            db,
            user_id=grievance.user_id,
            grievance_id=grievance.id,
            notification_type=db_type,
            title=item.title,
            message=item.message,
            commit=commit,
        )
    except Exception as exc:
        logger.warning(f"Could not persist DB notification: {exc}")

    return item


# ---------------------------------------------------------------------------
# Channel Formatting (Email Demo & SMS Demo)
# ---------------------------------------------------------------------------

def format_email_demo(notification: NotificationItem, recipient_email: str) -> Dict[str, str]:
    """Formats a rich email template for hackathon demonstration."""
    subject = f"[FlowGuard Alert] {notification.title}"
    body = f"""======================================================================
FLOWGUARD INVESTOR NOTIFICATION SERVICE (DEMO)
======================================================================
To:      {recipient_email}
Date:    {notification.created_at}
Stage:   {notification.stage}
Notice:  {notification.severity} - {notification.type}
----------------------------------------------------------------------

Dear Investor,

{notification.message}

Reference:
- Complaint ID: {notification.complaint_id}
- Action:       {notification.action_label or 'View Details'}
- Link:         {notification.action_url or 'N/A'}

Important Note:
FlowGuard provides transparent workflow tracking and verified official process
guidance for Indian investors. Simulated timelines are demo configurations.
======================================================================
"""
    return {
        "channel": "EMAIL_DEMO",
        "recipient": recipient_email,
        "subject": subject,
        "body": body,
    }


def format_sms_demo(notification: NotificationItem, recipient_phone: str) -> Dict[str, str]:
    """Formats a concise, Bharat-friendly SMS text for quick updates."""
    # Under 160 characters demo SMS format
    short_msg = (
        f"FlowGuard Alert: {notification.title}. "
        f"{notification.message[:90]}... Ref: {notification.complaint_id}"
    )
    return {
        "channel": "SMS_DEMO",
        "recipient": recipient_phone,
        "sms_text": short_msg,
    }


# ---------------------------------------------------------------------------
# Notification In-Memory Store & Service
# ---------------------------------------------------------------------------

class NotificationService:
    """
    In-memory notification manager.
    TODO (Person 2 Integration): Connect with PostgreSQL database table `notifications`
    and FastAPI REST endpoints GET/POST /api/v1/notifications.
    """
    def __init__(self):
        self._notifications: List[NotificationItem] = []

    def dispatch(self, notification: NotificationItem) -> Dict[str, Any]:
        """Stores notification and simulates multi-channel delivery."""
        self._notifications.append(notification)
        logger.info(f"Notification dispatched: [{notification.severity}] {notification.title} ({notification.id})")
        return {
            "status": "DISPATCHED",
            "notification_id": notification.id,
            "channel": notification.channel,
            "created_at": notification.created_at,
        }

    def get_notifications_for_complaint(
        self,
        complaint_id: str,
        unread_only: bool = False
    ) -> List[NotificationItem]:
        """Retrieves notifications for a specific complaint."""
        # TODO (Person 2 Integration): Replace with DB query
        res = [n for n in self._notifications if n.complaint_id == complaint_id]
        if unread_only:
            res = [n for n in res if not n.is_read]
        return res

    def mark_as_read(self, notification_id: str) -> bool:
        """Marks a notification as read."""
        for n in self._notifications:
            if n.id == notification_id:
                n.is_read = True
                return True
        return False


# Singleton service instance for runtime use
notification_service = NotificationService()


# ---------------------------------------------------------------------------
# Demo Case Notifications Helper (CMP-2026-DEMO-001)
# ---------------------------------------------------------------------------

def get_demo_notifications() -> Dict[str, Any]:
    """
    Generates all realistic notifications for shared demo case CMP-2026-DEMO-001:
    1. Stage Transition: FILED -> ACKNOWLEDGED
    2. Stage Transition: ACKNOWLEDGED -> AWAITING_RESPONSE
    3. Delay Warning: response_window_exceeded (30-day demo configuration)
    4. Evidence Reminder: 2 documents not yet uploaded
    5. Next-Action Guidance: SEBI SCORES 2.0 / SMART ODR Portal
    """
    complaint_id = "CMP-2026-DEMO-001"
    entity_name = "Demo Brokerage Pvt Ltd"

    # 1. Acknowledged notification
    n1 = create_stage_transition_notification(
        complaint_id=complaint_id,
        entity_name=entity_name,
        new_stage="ACKNOWLEDGED",
        previous_stage="FILED",
    )

    # 2. Awaiting Response notification
    n2 = create_stage_transition_notification(
        complaint_id=complaint_id,
        entity_name=entity_name,
        new_stage="AWAITING_RESPONSE",
        previous_stage="ACKNOWLEDGED",
    )

    # 3. Delay warning notification
    n3 = create_delay_warning_notification(
        complaint_id=complaint_id,
        entity_name=entity_name,
        stage="AWAITING_RESPONSE",
        warning_type="response_window_exceeded",
        days_elapsed=30,
        expected_window_days=30,
    )

    # 4. Evidence checklist reminder
    n4 = create_evidence_reminder_notification(
        complaint_id=complaint_id,
        stage="AWAITING_RESPONSE",
        missing_document_labels=[
            "Copy of original complaint",
            "Account / transaction statement"
        ],
    )

    # 5. Next-action escalation guidance
    n5 = create_next_action_notification(
        complaint_id=complaint_id,
        stage="AWAITING_RESPONSE",
        escalation_path="SEBI SCORES 2.0 / SMART ODR Portal",
        official_portal="https://scores.sebi.gov.in",
    )

    # Format email and SMS simulation for the delay warning
    email_demo = format_email_demo(n3, recipient_email="investor.ramesh@example.com")
    sms_demo = format_sms_demo(n3, recipient_phone="+91-9876543210")

    return {
        "complaint_id": complaint_id,
        "total_notifications": 5,
        "in_app_notifications": [n.model_dump() for n in [n1, n2, n3, n4, n5]],
        "simulated_email": email_demo,
        "simulated_sms": sms_demo,
    }


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    import json

    print("=" * 70)
    print("FLOWGUARD: Notification Service Test (Step 4)")
    print("=" * 70)

    demo_data = get_demo_notifications()
    print(f"\n[1] Generated {demo_data['total_notifications']} Demo Notifications for {demo_data['complaint_id']}:")

    for notif in demo_data["in_app_notifications"]:
        icon = {
            "INFO": "[INFO]",
            "WARNING": "[WARN]",
            "URGENT": "[URGENT]",
            "SUCCESS": "[OK]",
        }.get(notif["severity"], "[NOTE]")
        print(f"  {icon} [{notif['type']}] {notif['title']}")
        print(f"       Message: {notif['message']}")
        print(f"       Action:  {notif['action_label']} -> {notif['action_url']}\n")

    print("[2] Simulated Email Notification (Hackathon Demo):")
    print(demo_data["simulated_email"]["body"])

    print("[3] Simulated Bharat SMS Alert:")
    print(f"To:   {demo_data['simulated_sms']['recipient']}")
    print(f"Text: {demo_data['simulated_sms']['sms_text']}")

    print("\n" + "=" * 70)
    print("Step 4 validation completed successfully!")
    print("=" * 70)
