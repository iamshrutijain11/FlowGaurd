import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import (
    STAGE_LABELS,
    EventSource,
    EventType,
    GrievanceStage,
    NotificationType,
)
from app.models.grievance import Grievance
from app.models.user import User
from app.schemas.grievance import GrievanceCreate, GrievanceOut, GrievanceUpdate
from app.services import event_service, notification_service
from app.utils.time import as_utc, utcnow

_MAIN_PATH = [
    GrievanceStage.FILED,
    GrievanceStage.ACKNOWLEDGED,
    GrievanceStage.AWAITING_RESPONSE,
    GrievanceStage.RESPONSE_RECEIVED,
]
_STAGE_DESCRIPTIONS = {
    GrievanceStage.FILED: "Complaint filed.",
    GrievanceStage.ACKNOWLEDGED: "Acknowledgement recorded.",
    GrievanceStage.AWAITING_RESPONSE: "Status recorded as Awaiting Response.",
    GrievanceStage.RESPONSE_RECEIVED: "Response recorded.",
    GrievanceStage.RESOLVED: "Grievance marked as resolved.",
    GrievanceStage.FURTHER_ACTION: "Status recorded as Further Action.",
}


def _stage_path(target: GrievanceStage) -> list[GrievanceStage]:
    """Ordered stages from FILED up to `target` (used to backfill the timeline)."""
    if target in _MAIN_PATH:
        return _MAIN_PATH[: _MAIN_PATH.index(target) + 1]
    return [*_MAIN_PATH, target]  # RESOLVED / FURTHER_ACTION follow RESPONSE_RECEIVED


def _check_transition(current: GrievanceStage, new: GrievanceStage) -> None:
    """Delegates to Person 3's state machine once it exists.

    Expected signature in app/workflow/state_machine.py:
        validate_transition(from_stage: str, to_stage: str) -> bool
    Until that module is merged, any valid enum value is accepted."""
    try:
        from app.workflow.state_machine import validate_transition  # type: ignore
    except ImportError:
        return
    if not validate_transition(current.value, new.value):
        raise AppError(
            "INVALID_STAGE_TRANSITION",
            f"Cannot move a grievance from {current.value} to {new.value}.",
            409,
        )


# ---------------------------------------------------------------- create / read

def create_grievance(db: Session, user: User, data: GrievanceCreate) -> Grievance:
    dup = db.scalar(
        select(Grievance).where(
            Grievance.user_id == user.id, Grievance.complaint_id == data.complaint_id
        )
    )
    if dup:
        raise AppError(
            "DUPLICATE_COMPLAINT_ID", "You have already added a grievance with this complaint ID.", 409
        )

    target = data.current_stage or (
        GrievanceStage.ACKNOWLEDGED if data.acknowledgement_date else GrievanceStage.FILED
    )
    now = utcnow()
    ack_time = data.acknowledgement_date or data.submission_date

    grievance = Grievance(
        user_id=user.id,
        complaint_id=data.complaint_id,
        entity_name=data.entity_name,
        issue_type=data.issue_type,
        issue_description=data.issue_description,
        submission_date=data.submission_date,
        current_stage=target,
        status_updated_at=data.submission_date,
    )
    db.add(grievance)
    db.flush()

    last_time = data.submission_date
    for stage in _stage_path(target):
        if stage == GrievanceStage.FILED:
            when = data.submission_date
        elif stage in (GrievanceStage.ACKNOWLEDGED, GrievanceStage.AWAITING_RESPONSE):
            when = ack_time
        else:
            when = max(now, ack_time)
        last_time = when
        event_service.create_event(
            db,
            grievance.id,
            EventType(stage.value),
            _STAGE_DESCRIPTIONS[stage],
            source=EventSource.USER,
            event_time=when,
            metadata={} if stage == GrievanceStage.FILED else {"recorded_at_creation": True},
            commit=False,
        )
    grievance.status_updated_at = last_time
    db.commit()
    return grievance


def get_grievance(db: Session, grievance_id: uuid.UUID | str) -> Grievance | None:
    """Unscoped lookup for internal callers (workflow/AI). API routes use get_owned_grievance."""
    if isinstance(grievance_id, uuid.UUID):
        return db.get(Grievance, grievance_id)
    try:
        val = uuid.UUID(str(grievance_id))
        g = db.get(Grievance, val)
        if g:
            return g
    except (ValueError, AttributeError):
        pass
    return db.scalar(select(Grievance).where(Grievance.complaint_id == str(grievance_id)))


def get_owned_grievance(db: Session, grievance_id: uuid.UUID | str, user: User) -> Grievance:
    g = None
    if isinstance(grievance_id, uuid.UUID):
        g = db.get(Grievance, grievance_id)
    else:
        try:
            val = uuid.UUID(str(grievance_id))
            g = db.get(Grievance, val)
        except (ValueError, AttributeError):
            g = None
        if not g:
            g = db.scalar(
                select(Grievance).where(
                    Grievance.user_id == user.id,
                    Grievance.complaint_id == str(grievance_id),
                )
            )
    if not g or g.user_id != user.id:  # same error for both: don't reveal other users' IDs
        raise AppError("GRIEVANCE_NOT_FOUND", "Grievance not found", 404)
    return g


def list_grievances(db: Session, user: User, stage: GrievanceStage | None = None) -> list[Grievance]:
    q = select(Grievance).where(Grievance.user_id == user.id)
    if stage:
        q = q.where(Grievance.current_stage == stage)
    return list(db.scalars(q.order_by(Grievance.updated_at.desc())))


def get_active_grievances(db: Session) -> list[Grievance]:
    """For the scheduler: every grievance that is not RESOLVED (all users)."""
    q = select(Grievance).where(Grievance.current_stage != GrievanceStage.RESOLVED)
    return list(db.scalars(q))


# ---------------------------------------------------------------- update

def update_grievance_stage(
    db: Session,
    grievance: Grievance,
    new_stage: GrievanceStage,
    *,
    source: EventSource = EventSource.USER,
    description: str | None = None,
    event_time: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> Grievance:
    """Moves the grievance to `new_stage`, appends a timeline event and notifies the owner."""
    previous = grievance.current_stage
    if new_stage == previous:
        return grievance
    _check_transition(previous, new_stage)

    when = event_time or utcnow()
    grievance.current_stage = new_stage
    grievance.status_updated_at = when
    label = STAGE_LABELS[new_stage]
    event_service.create_event(
        db,
        grievance.id,
        EventType(new_stage.value),
        description or f"Status changed to {label}.",
        source=source,
        event_time=when,
        metadata={"previous_stage": previous.value, "new_stage": new_stage.value, **(metadata or {})},
        commit=False,
    )
    resolved = new_stage == GrievanceStage.RESOLVED
    notification_service.create_notification(
        db,
        user_id=grievance.user_id,
        grievance_id=grievance.id,
        notification_type=NotificationType.GRIEVANCE_RESOLVED if resolved else NotificationType.STATUS_CHANGED,
        title="Grievance resolved" if resolved else "Grievance status updated",
        message=f"Your grievance {grievance.complaint_id} is now recorded as: {label}.",
        commit=False,
    )
    db.commit() if commit else db.flush()
    return grievance


def update_grievance(
    db: Session, grievance: Grievance, data: GrievanceUpdate, source: EventSource = EventSource.USER
) -> Grievance:
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise AppError("NO_CHANGES", "No fields were provided to update.", 400)

    new_stage = changes.pop("current_stage", None)
    diff: dict[str, dict[str, Any]] = {}
    for field, value in changes.items():
        if value is None:
            continue
        old = getattr(grievance, field)
        if old != value:
            diff[field] = {"old": old, "new": value}
            setattr(grievance, field, value)
    if diff:
        # History is never silently altered: record what changed.
        event_service.create_event(
            db, grievance.id, EventType.DETAILS_UPDATED, "Grievance details updated.",
            source=source, metadata={"changes": diff}, commit=False,
        )
    if new_stage is not None:
        update_grievance_stage(db, grievance, new_stage, source=source, commit=False)
    grievance.updated_at = utcnow()
    db.commit()
    return grievance


# ---------------------------------------------------------------- presentation

def grievance_out(grievance: Grievance) -> GrievanceOut:
    events = event_service.list_events_for(grievance)
    out = GrievanceOut.model_validate(grievance)
    out.warning = event_service.get_active_warning(grievance, events)
    out.last_event_at = max((as_utc(e.event_time) for e in events), default=None)
    return out
