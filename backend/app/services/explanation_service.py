"""PLACEHOLDER explanation provider (template text, NOT an LLM).

Person 4 replaces `get_explanation` with the grounded AI summariser. Keep the signature and the
ExplanationOut shape. The frontend labels this card as AI-generated, so `is_placeholder` lets
the UI/demo distinguish mock output until the real implementation lands."""
from sqlalchemy.orm import Session

from app.models.enums import STAGE_LABELS
from app.models.grievance import Grievance
from app.schemas.grievance import ExplanationOut
from app.services import event_service
from app.utils.time import utcnow


def get_explanation(db: Session, grievance: Grievance) -> ExplanationOut:
    events = event_service.list_events_for(grievance)
    warning = event_service.get_active_warning(grievance, events)
    stage_label = STAGE_LABELS[grievance.current_stage]
    recorded = [e.event_type.value.replace("_", " ").title() for e in events if e.event_type.value in {
        "FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE", "RESPONSE_RECEIVED", "RESOLVED", "FURTHER_ACTION"}]
    return ExplanationOut(
        current_situation=f"Your grievance is currently recorded as: {stage_label}.",
        timeline_summary="Recorded so far: " + (", ".join(recorded) if recorded else "no events") + ".",
        warning_explanation=(warning.reason if warning else None),
        missing_information=[],
        next_step_summary="Review the suggested next step shown for this grievance.",
        generated_at=utcnow(),
    )
