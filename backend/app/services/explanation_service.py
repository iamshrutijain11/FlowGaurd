"""Dynamic plain-language explanation provider.

Generates a structured explanation for ANY grievance based on its current
stage, event history, warnings, and documents. No LLM required at this stage —
all text is grounded in recorded facts only.

Person 4 may replace the body of `get_explanation` with an LLM call
(via app/ai/summarizer.py) while keeping the function signature and
ExplanationOut schema unchanged.
"""
from __future__ import annotations

from datetime import timezone
from typing import TYPE_CHECKING

from app.models.enums import DocumentType, EventType, GrievanceStage, WarningType, STAGE_LABELS
from app.schemas.grievance import ExplanationOut
from app.services import event_service
from app.utils.time import as_utc, utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.grievance import Grievance

# ── Stage situation messages ──────────────────────────────────────────────────

_SITUATION: dict[GrievanceStage, str] = {
    GrievanceStage.FILED: (
        "Your grievance has been filed and is waiting for an acknowledgement from the entity."
    ),
    GrievanceStage.ACKNOWLEDGED: (
        "Your grievance has been acknowledged by the entity and is now awaiting a formal response."
    ),
    GrievanceStage.AWAITING_RESPONSE: (
        "Your grievance is currently waiting for a response from the entity. "
        "No response has been recorded in FlowGuard yet."
    ),
    GrievanceStage.RESPONSE_RECEIVED: (
        "A response to your grievance has been recorded. "
        "You may want to review it and decide whether you are satisfied with the outcome."
    ),
    GrievanceStage.RESOLVED: (
        "Your grievance has been marked as resolved."
    ),
    GrievanceStage.FURTHER_ACTION: (
        "Your grievance has been escalated for further action. "
        "Additional steps may be available to you through the official grievance process."
    ),
}

_NEXT_STEP: dict[GrievanceStage, str] = {
    GrievanceStage.FILED: (
        "Consider following up if you have not received an acknowledgement within the expected timeframe."
    ),
    GrievanceStage.ACKNOWLEDGED: (
        "Wait for the entity's formal response. Keep your acknowledgement document safe for your records."
    ),
    GrievanceStage.AWAITING_RESPONSE: (
        "If no response has been received within a reasonable period, "
        "consider sending a follow-up through the official grievance channel."
    ),
    GrievanceStage.RESPONSE_RECEIVED: (
        "Review the response carefully. If you are not satisfied, "
        "you may be able to escalate through the official grievance process."
    ),
    GrievanceStage.RESOLVED: (
        "No further action is required. Keep all documents related to this grievance for your records."
    ),
    GrievanceStage.FURTHER_ACTION: (
        "Follow the applicable official process for escalation. "
        "Gather all correspondence and documents related to this grievance before proceeding."
    ),
}

# ── Warning explanation messages ──────────────────────────────────────────────

_WARNING_EXPLANATIONS: dict[str, str] = {
    WarningType.POTENTIAL_DELAY.value: (
        "FlowGuard detected that this grievance has remained in its current stage "
        "longer than the configured monitoring window. This is a FlowGuard observation — "
        "not a regulatory conclusion. It means a follow-up may be appropriate."
    ),
    WarningType.FOLLOW_UP_DUE.value: (
        "FlowGuard suggests that a follow-up may be timely given the time elapsed "
        "since the last recorded activity."
    ),
    WarningType.MISSING_INFORMATION.value: (
        "FlowGuard has noticed that some information or documents that may be useful "
        "for your grievance record have not yet been uploaded."
    ),
    WarningType.DOCUMENT_REQUIRED.value: (
        "A document that may support your grievance record appears to be missing. "
        "Consider uploading it to keep your record complete."
    ),
    WarningType.NO_RECENT_UPDATE.value: (
        "No activity has been recorded on this grievance for an extended period. "
        "You may want to check on its current status."
    ),
}


# ── Helper: build human-readable timeline summary ────────────────────────────

def _build_timeline_summary(events) -> str:
    stage_events = [
        e for e in events
        if e.event_type.value in {s.value for s in GrievanceStage}
    ]
    if not stage_events:
        return "No stage events have been recorded yet."

    parts = []
    for e in stage_events:
        dt = as_utc(e.event_time)
        date_str = f"{dt.day} {dt.strftime('%b %Y')}"
        label = STAGE_LABELS.get(GrievanceStage(e.event_type.value), e.event_type.value.replace("_", " ").title())
        parts.append(f"{date_str}: {label}")

    return "Recorded timeline — " + " → ".join(parts) + "."


# ── Helper: detect missing evidence ──────────────────────────────────────────

def _find_missing_info(grievance: Grievance, events) -> list[str]:
    missing = []
    stage = grievance.current_stage

    # Past FILED but no acknowledgement doc?
    if stage != GrievanceStage.FILED and stage != GrievanceStage.RESOLVED:
        has_ack = any(
            doc.document_type == DocumentType.ACKNOWLEDGEMENT
            for doc in grievance.documents
        )
        if not has_ack:
            missing.append(
                "No acknowledgement document has been uploaded. "
                "This may be useful to keep in your grievance record."
            )

    # Awaiting or past response but no response doc?
    if stage in (GrievanceStage.RESPONSE_RECEIVED, GrievanceStage.FURTHER_ACTION):
        has_response_doc = any(
            doc.document_type == DocumentType.RESPONSE
            for doc in grievance.documents
        )
        if not has_response_doc:
            missing.append(
                "No response document has been uploaded. "
                "If you have received a written response, consider uploading it."
            )

    # No description provided?
    if not grievance.issue_description or grievance.issue_description.strip() in ("", "Demo transaction grievance used for the FlowGuard walkthrough."):
        pass  # Not a user-facing warning for demo case

    return missing


# ── Main function ─────────────────────────────────────────────────────────────

def get_explanation(db: Session, grievance: Grievance) -> ExplanationOut:
    """Generate a dynamic plain-language explanation for ANY grievance.

    All text is grounded in recorded facts only.
    Nothing is fabricated — if information is unavailable, it says so explicitly.
    """
    events = event_service.list_events_for(grievance)
    warning = event_service.get_active_warning(grievance, events)
    stage = grievance.current_stage

    # Current situation
    current_situation = _SITUATION.get(
        stage,
        f"Your grievance is currently recorded as: {STAGE_LABELS.get(stage, stage.value)}."
    )

    # Timeline summary
    timeline_summary = _build_timeline_summary(events)

    # Warning explanation
    warning_explanation: str | None = None
    if warning:
        warning_explanation = _WARNING_EXPLANATIONS.get(
            warning.type,
            f"FlowGuard has recorded a {warning.type.replace('_', ' ').lower()} observation for this grievance."
        )
        if warning.reason:
            warning_explanation += f" Detail: {warning.reason}"

    # Missing information
    missing_information = _find_missing_info(grievance, events)

    # Next step
    next_step_summary = _NEXT_STEP.get(
        stage,
        "Review your grievance details and keep all related documents safely."
    )

    # If a delay warning is active, override next step with a follow-up suggestion
    if warning and warning.type == WarningType.POTENTIAL_DELAY.value and stage != GrievanceStage.RESOLVED:
        next_step_summary = (
            "FlowGuard suggests that a follow-up may be appropriate. "
            "Consider reaching out through the official grievance channel with your complaint reference number."
        )

    return ExplanationOut(
        current_situation=current_situation,
        timeline_summary=timeline_summary,
        warning_explanation=warning_explanation,
        missing_information=missing_information,
        next_step_summary=next_step_summary,
        generated_at=utcnow(),
        is_placeholder=False,  # This is real dynamic output, not a mock
    )
