"""Dynamic next-action provider.

Determines the appropriate action category and human-readable guidance
for ANY grievance based on its current stage and active warnings.

The action CATEGORY (NO_ACTION / FOLLOW_UP / REVIEW_DOCUMENTS / FURTHER_ACTION_AVAILABLE)
is determined deterministically by the workflow engine logic.

The wording and required documents are stage-aware.
No regulatory facts are invented — all guidance is conservative and general.

Person 4 may wire in verified guidance JSON files (app/ai/guidance_data/)
to replace or extend the `official_source` field.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.enums import ActionType, GrievanceStage, WarningType
from app.schemas.grievance import NextActionOut
from app.services import event_service

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.grievance import Grievance


# ── Stage-level action definitions ───────────────────────────────────────────

_STAGE_ACTIONS: dict[GrievanceStage, dict] = {
    GrievanceStage.FILED: {
        "type": ActionType.NO_ACTION.value,
        "title": "Wait for acknowledgement",
        "description": (
            "Your complaint has been filed. Wait for the entity to acknowledge it. "
            "Keep your complaint reference number and submission proof safe."
        ),
        "required_documents": ["Complaint reference number", "Proof of submission"],
    },
    GrievanceStage.ACKNOWLEDGED: {
        "type": ActionType.NO_ACTION.value,
        "title": "Wait for the entity's response",
        "description": (
            "Your complaint has been acknowledged. The entity is expected to review it "
            "and provide a response. Keep your acknowledgement document safe."
        ),
        "required_documents": ["Complaint reference number", "Acknowledgement document"],
    },
    GrievanceStage.AWAITING_RESPONSE: {
        "type": ActionType.NO_ACTION.value,
        "title": "Awaiting response — no action needed yet",
        "description": (
            "Your grievance is awaiting a response from the entity. "
            "No action is required from you right now."
        ),
        "required_documents": ["Complaint reference number", "Acknowledgement document"],
    },
    GrievanceStage.RESPONSE_RECEIVED: {
        "type": ActionType.REVIEW_DOCUMENTS.value,
        "title": "Review the response",
        "description": (
            "A response has been recorded. Review it carefully to determine if "
            "you are satisfied with the outcome. If not, further action may be available."
        ),
        "required_documents": [
            "Complaint reference number",
            "Acknowledgement document",
            "Entity's response",
        ],
    },
    GrievanceStage.RESOLVED: {
        "type": ActionType.NO_ACTION.value,
        "title": "Grievance resolved",
        "description": (
            "This grievance has been marked as resolved. No further action is required. "
            "Keep all related documents for your records."
        ),
        "required_documents": [],
    },
    GrievanceStage.FURTHER_ACTION: {
        "type": ActionType.FURTHER_ACTION_AVAILABLE.value,
        "title": "Further action may be available",
        "description": (
            "Your grievance has been escalated. Additional steps may be available "
            "through the applicable official grievance process. "
            "Verified guidance will appear here once wired in."
        ),
        "required_documents": [
            "Complaint reference number",
            "Acknowledgement document",
            "Entity's response",
            "Any supporting correspondence",
        ],
    },
}

# ── Follow-up override (when POTENTIAL_DELAY warning is active) ───────────────

_FOLLOW_UP_ACTION = {
    "type": ActionType.FOLLOW_UP.value,
    "title": "Follow-up may be appropriate",
    "description": (
        "No response has been recorded within FlowGuard's configured monitoring window. "
        "A follow-up through the applicable official grievance process may be appropriate. "
        "When following up, include your complaint reference number, submission date, "
        "and acknowledgement document."
    ),
    "required_documents": [
        "Complaint reference number",
        "Submission date",
        "Acknowledgement document",
        "Any prior correspondence",
    ],
}

_REMINDER_ACTION = {
    "type": ActionType.FOLLOW_UP.value,
    "title": "Consider sending a follow-up",
    "description": (
        "Some time has passed without a recorded response. "
        "While this is within FlowGuard's reminder window, you may want to check on the status "
        "of your grievance by contacting the entity."
    ),
    "required_documents": [
        "Complaint reference number",
        "Acknowledgement document",
    ],
}

_MISSING_INFO_ACTION = {
    "type": ActionType.REVIEW_DOCUMENTS.value,
    "title": "Complete your grievance record",
    "description": (
        "FlowGuard has detected that some information or documents that may support "
        "your grievance record have not yet been uploaded. "
        "Consider uploading them to keep your record complete."
    ),
    "required_documents": [
        "Acknowledgement document",
        "Any supporting evidence",
    ],
}


# ── Main function ─────────────────────────────────────────────────────────────

def get_next_action(db: Session, grievance: Grievance) -> NextActionOut:
    """Determine the recommended next action for ANY grievance.

    Priority:
      1. RESOLVED → always NO_ACTION
      2. Active POTENTIAL_DELAY warning → FOLLOW_UP
      3. Active FOLLOW_UP_DUE warning → FOLLOW_UP (softer)
      4. Active MISSING_INFORMATION / DOCUMENT_REQUIRED → REVIEW_DOCUMENTS
      5. Stage defaults above
    """
    stage = grievance.current_stage

    # Resolved: always no action
    if stage == GrievanceStage.RESOLVED:
        action = _STAGE_ACTIONS[GrievanceStage.RESOLVED]
        return NextActionOut(**action, official_source=None, is_placeholder=False)

    # Load active warning
    from app.services.event_service import list_events_for, get_active_warning
    events = list_events_for(grievance)
    warning = get_active_warning(grievance, events)

    if warning:
        wtype = warning.type

        if wtype == WarningType.POTENTIAL_DELAY.value:
            action = _FOLLOW_UP_ACTION.copy()

        elif wtype == WarningType.FOLLOW_UP_DUE.value:
            action = _REMINDER_ACTION.copy()

        elif wtype in (WarningType.MISSING_INFORMATION.value, WarningType.DOCUMENT_REQUIRED.value):
            action = _MISSING_INFO_ACTION.copy()

        else:
            # NO_RECENT_UPDATE or unknown — use stage default
            action = _STAGE_ACTIONS.get(stage, {
                "type": ActionType.NO_ACTION.value,
                "title": "No action needed right now",
                "description": "Your grievance is being monitored by FlowGuard.",
                "required_documents": [],
            }).copy()
    else:
        # No warning → use stage default
        action = _STAGE_ACTIONS.get(stage, {
            "type": ActionType.NO_ACTION.value,
            "title": "No action needed right now",
            "description": "Your grievance is progressing within FlowGuard's configured monitoring window.",
            "required_documents": [],
        }).copy()

    return NextActionOut(
        type=action["type"],
        title=action["title"],
        description=action["description"],
        required_documents=action.get("required_documents", []),
        official_source=None,   # Person 4 wires in verified guidance here
        is_placeholder=False,
    )
