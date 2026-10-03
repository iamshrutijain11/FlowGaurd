from sqlalchemy.orm import Session

from app.models.enums import GrievanceStage, WarningType
from app.models.user import User
from app.schemas.grievance import DashboardSummary
from app.services import event_service, grievance_service


def get_summary(db: Session, user: User) -> DashboardSummary:
    active = delayed = resolved = 0
    for g in grievance_service.list_grievances(db, user):
        if g.current_stage == GrievanceStage.RESOLVED:
            resolved += 1
            continue
        active += 1
        w = event_service.get_active_warning(g, event_service.list_events_for(g))
        if w and w.type == WarningType.POTENTIAL_DELAY.value:
            delayed += 1
    return DashboardSummary(
        active=active, on_track=active - delayed, potentially_delayed=delayed, resolved=resolved
    )
