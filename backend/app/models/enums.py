"""Shared enums. Values are the FROZEN contract names - do not rename."""
import enum


class GrievanceStage(str, enum.Enum):
    FILED = "FILED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    RESOLVED = "RESOLVED"
    FURTHER_ACTION = "FURTHER_ACTION"


class WarningType(str, enum.Enum):
    POTENTIAL_DELAY = "POTENTIAL_DELAY"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    NO_RECENT_UPDATE = "NO_RECENT_UPDATE"


class EventType(str, enum.Enum):
    # stage events (same names as GrievanceStage)
    FILED = "FILED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    RESOLVED = "RESOLVED"
    FURTHER_ACTION = "FURTHER_ACTION"
    # warning events (same names as WarningType) - FlowGuard observations, not official facts
    POTENTIAL_DELAY = "POTENTIAL_DELAY"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    NO_RECENT_UPDATE = "NO_RECENT_UPDATE"
    # other timeline entries
    REMINDER = "REMINDER"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    DETAILS_UPDATED = "DETAILS_UPDATED"
    NOTE_ADDED = "NOTE_ADDED"
    FOLLOW_UP_SENT = "FOLLOW_UP_SENT"


WARNING_EVENT_TYPES = frozenset(EventType(w.value) for w in WarningType)
# Event types an investor may add themselves via POST /events
USER_ALLOWED_EVENT_TYPES = frozenset({EventType.NOTE_ADDED, EventType.FOLLOW_UP_SENT})


class EventSource(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    AI = "AI"
    ADMIN = "ADMIN"


class DocumentType(str, enum.Enum):
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    RESPONSE = "RESPONSE"
    SCREENSHOT = "SCREENSHOT"
    SUPPORTING_EVIDENCE = "SUPPORTING_EVIDENCE"
    OTHER = "OTHER"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NotificationType(str, enum.Enum):
    STATUS_CHANGED = "STATUS_CHANGED"
    POTENTIAL_DELAY = "POTENTIAL_DELAY"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    GRIEVANCE_RESOLVED = "GRIEVANCE_RESOLVED"


class ActionType(str, enum.Enum):
    """Next-action / escalation categories (determined by the workflow engine)."""
    NO_ACTION = "NO_ACTION"
    FOLLOW_UP = "FOLLOW_UP"
    REVIEW_DOCUMENTS = "REVIEW_DOCUMENTS"
    FURTHER_ACTION_AVAILABLE = "FURTHER_ACTION_AVAILABLE"


class EscalationStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


STAGE_LABELS = {
    GrievanceStage.FILED: "Filed",
    GrievanceStage.ACKNOWLEDGED: "Acknowledged",
    GrievanceStage.AWAITING_RESPONSE: "Awaiting Response",
    GrievanceStage.RESPONSE_RECEIVED: "Response Received",
    GrievanceStage.RESOLVED: "Resolved",
    GrievanceStage.FURTHER_ACTION: "Further Action",
}
