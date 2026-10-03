"""PLACEHOLDER next-action provider.

Person 3 (workflow engine) decides the action CATEGORY; Person 4 (guidance module) supplies
verified wording/sources. Replace the body of `get_next_action` - keep the signature and the
NextActionOut shape so the API contract stays frozen. No regulatory facts live here."""
from sqlalchemy.orm import Session

from app.models.enums import ActionType, GrievanceStage, WarningType
from app.models.grievance import Grievance
from app.schemas.grievance import NextActionOut
from app.services import event_service


def get_next_action(db: Session, grievance: Grievance) -> NextActionOut:
    stage = grievance.current_stage
    warning = event_service.get_active_warning(grievance, event_service.list_events_for(grievance))

    if stage == GrievanceStage.RESOLVED:
        return NextActionOut(
            type=ActionType.NO_ACTION.value,
            title="No action needed",
            description="This grievance is recorded as resolved.",
        )
    if stage == GrievanceStage.RESPONSE_RECEIVED:
        return NextActionOut(
            type=ActionType.REVIEW_DOCUMENTS.value,
            title="Review the response",
            description="A response has been recorded. You may want to review it and keep it with your grievance record.",
        )
    if stage == GrievanceStage.FURTHER_ACTION:
        return NextActionOut(
            type=ActionType.FURTHER_ACTION_AVAILABLE.value,
            title="Further action may be available",
            description="Further steps may be relevant. Verified guidance will appear here.",
        )
    if warning and warning.type == WarningType.POTENTIAL_DELAY.value:
        return NextActionOut(
            type=ActionType.FOLLOW_UP.value,
            title="Follow-up may be appropriate",
            description="No response has been recorded within FlowGuard's configured monitoring window. "
            "A follow-up through the applicable official grievance process may be appropriate.",
        )
    return NextActionOut(
        type=ActionType.NO_ACTION.value,
        title="No action needed right now",
        description="Your grievance is progressing within FlowGuard's configured monitoring window.",
    )
