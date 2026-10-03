"""Timeline / warning persistence. Person 3 (workflow) and Person 4 (AI) call these - do not
duplicate persistence logic elsewhere."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    WARNING_EVENT_TYPES,
    EventSource,
    EventType,
    WarningType,
)
from app.models.event import GrievanceEvent
from app.models.grievance import Grievance
from app.schemas.grievance import WarningOut
from app.utils.time import as_utc, utcnow


def create_event(
    db: Session,
    grievance_id: uuid.UUID,
    event_type: EventType,
    description: str,
    *,
    source: EventSource = EventSource.SYSTEM,
    event_time: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> GrievanceEvent:
    event = GrievanceEvent(
        grievance_id=grievance_id,
        event_type=event_type,
        event_time=event_time or utcnow(),
        source=source,
        description=description,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.commit() if commit else db.flush()
    return event


def list_events(db: Session, grievance_id: uuid.UUID) -> list[GrievanceEvent]:
    q = (
        select(GrievanceEvent)
        .where(GrievanceEvent.grievance_id == grievance_id)
        .order_by(GrievanceEvent.event_time, GrievanceEvent.created_at)
    )
    return list(db.scalars(q))


def create_warning_event(
    db: Session,
    grievance: Grievance,
    warning_type: WarningType,
    *,
    rule_id: str,
    reason: str,
    severity: str = "WARNING",
    based_on_event_id: uuid.UUID | None = None,
    triggered_at: datetime | None = None,
    extra: dict[str, Any] | None = None,
    commit: bool = True,
) -> GrievanceEvent:
    """Stores a FlowGuard warning as a SYSTEM event (explainable: rule, reason, based_on_event).

    Idempotent: if the same warning type + rule was already recorded since the grievance entered
    its current stage, the existing event is returned instead of creating a duplicate."""
    since = as_utc(grievance.status_updated_at)
    for e in list_events(db, grievance.id):
        if (
            e.event_type.value == warning_type.value
            and (e.metadata_json or {}).get("rule_id") == rule_id
            and as_utc(e.event_time) >= since
        ):
            return e

    metadata = {
        "severity": severity,
        "rule_id": rule_id,
        "reason": reason,
        "based_on_event": str(based_on_event_id) if based_on_event_id else None,
        "stage": grievance.current_stage.value,
        **(extra or {}),
    }
    event = create_event(
        db,
        grievance.id,
        EventType(warning_type.value),
        reason,
        source=EventSource.SYSTEM,
        event_time=triggered_at,
        metadata=metadata,
        commit=commit,
    )
    try:
        from app.notifications.notifications import create_warning_notification_for_grievance
        create_warning_notification_for_grievance(
            db, grievance, warning_type, rule_id, reason, commit=commit
        )
    except Exception:
        pass
    return event


def get_active_warning(grievance: Grievance, events: list[GrievanceEvent]) -> WarningOut | None:
    """Latest FlowGuard warning raised since the grievance entered its current stage.
    Resolved grievances never show a warning. POTENTIAL_DELAY takes display priority."""
    if grievance.current_stage.value == "RESOLVED":
        return None
    since = as_utc(grievance.status_updated_at)
    candidates = [
        e for e in events if e.event_type in WARNING_EVENT_TYPES and as_utc(e.event_time) >= since
    ]
    if not candidates:
        return None
    latest = max(
        candidates,
        key=lambda e: (e.event_type == EventType.POTENTIAL_DELAY, as_utc(e.event_time)),
    )
    md = latest.metadata_json or {}
    return WarningOut(
        type=latest.event_type.value,
        severity=md.get("severity", "WARNING"),
        rule=md.get("rule_id"),
        reason=md.get("reason") or latest.description,
        triggered_at=latest.event_time,
        event_id=latest.id,
        based_on_event=md.get("based_on_event"),
    )


def list_events_for(grievance: Grievance) -> list[GrievanceEvent]:
    """Events from the loaded relationship, chronologically ordered."""
    return sorted(grievance.events, key=lambda e: (as_utc(e.event_time), as_utc(e.created_at)))
