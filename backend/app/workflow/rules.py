"""Rule functions for FlowGuard's deterministic grievance monitoring.

Each rule receives a Grievance ORM object and its pre-loaded list of GrievanceEvent objects.
Rules call `create_warning_event` (idempotent) to persist FlowGuard observations.

IMPORTANT: These rules detect *potential* delays based on configured demo windows.
They do NOT determine regulatory violations, wrongdoing, or legal liability.
All thresholds come from demo_rules.json — NOT from regulatory sources.
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from app.models.enums import (
    DocumentType,
    EventType,
    GrievanceStage,
    WarningType,
)
from app.services import event_service
from app.utils.time import as_utc, utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.event import GrievanceEvent
    from app.models.grievance import Grievance

logger = logging.getLogger("flowguard.workflow.rules")

# ── Load rule configuration ────────────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).parent / "config" / "demo_rules.json"

def _load_rules() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not load demo_rules.json: %s. Using defaults.", exc)
        return {}

_RULES: dict = _load_rules()


# ── Helper ─────────────────────────────────────────────────────────────────────

def _days_since(events: list[GrievanceEvent], stage: GrievanceStage) -> float | None:
    """Return days elapsed since the grievance entered `stage` (using the
    most recent matching stage event), or None if no such event found."""
    stage_events = [
        e for e in events if e.event_type.value == stage.value
    ]
    if not stage_events:
        return None
    latest = max(stage_events, key=lambda e: as_utc(e.event_time))
    delta = utcnow() - as_utc(latest.event_time)
    return delta.total_seconds() / 86400  # fractional days


def _has_subsequent_event(events: list[GrievanceEvent], after_stage: GrievanceStage, target_types: set[str]) -> bool:
    """Return True if a target event exists AFTER the given stage event."""
    stage_time = None
    for e in events:
        if e.event_type.value == after_stage.value:
            t = as_utc(e.event_time)
            if stage_time is None or t > stage_time:
                stage_time = t
    if stage_time is None:
        return False
    return any(
        e.event_type.value in target_types and as_utc(e.event_time) > stage_time
        for e in events
    )


def _get_stage_event(events: list[GrievanceEvent], stage: GrievanceStage):
    """Return the most recent event matching `stage`, or None."""
    matching = [e for e in events if e.event_type.value == stage.value]
    return max(matching, key=lambda e: as_utc(e.event_time)) if matching else None


# ── Rule 1: No acknowledgement received after filing ──────────────────────────

def rule_filed_no_acknowledgement(db: Session, grievance: Grievance, events: list[GrievanceEvent]) -> None:
    """Warn if a grievance has been FILED for too long without an ACKNOWLEDGED event."""
    if grievance.current_stage != GrievanceStage.FILED:
        return

    cfg = _RULES.get("FILED", {})
    warning_days = cfg.get("warning_after_days", 4)
    rule_id = cfg.get("rule_id", "DEMO_FILED_WINDOW")
    reminder_days = cfg.get("reminder_after_days", 2)

    days = _days_since(events, GrievanceStage.FILED)
    if days is None:
        return

    has_ack = _has_subsequent_event(events, GrievanceStage.FILED, {"ACKNOWLEDGED"})
    if has_ack:
        return

    filed_event = _get_stage_event(events, GrievanceStage.FILED)

    if days >= warning_days:
        event_service.create_warning_event(
            db, grievance, WarningType.NO_RECENT_UPDATE,
            rule_id=rule_id,
            reason=(
                f"No acknowledgement has been recorded {int(days)} day(s) after the complaint "
                f"was filed. (Demo window: {warning_days} days.)"
            ),
            based_on_event_id=filed_event.id if filed_event else None,
        )
    elif days >= reminder_days:
        event_service.create_warning_event(
            db, grievance, WarningType.FOLLOW_UP_DUE,
            rule_id=rule_id + "_REMINDER",
            reason=(
                f"No acknowledgement has been recorded {int(days)} day(s) after filing. "
                f"A follow-up may be appropriate. (Demo reminder window: {reminder_days} days.)"
            ),
            based_on_event_id=filed_event.id if filed_event else None,
        )


# ── Rule 2: No response received while AWAITING_RESPONSE ──────────────────────

def rule_awaiting_response_window(db: Session, grievance: Grievance, events: list[GrievanceEvent]) -> None:
    """Core delay-detection rule: warn if no response has been recorded within the configured window."""
    if grievance.current_stage not in (
        GrievanceStage.AWAITING_RESPONSE, GrievanceStage.ACKNOWLEDGED
    ):
        return

    # Pick the config block based on current stage
    stage_key = grievance.current_stage.value  # "AWAITING_RESPONSE" or "ACKNOWLEDGED"
    cfg = _RULES.get(stage_key, {})
    warning_days = cfg.get("warning_after_days", 5)
    reminder_days = cfg.get("reminder_after_days", 3)
    rule_id = cfg.get("rule_id", f"DEMO_{stage_key}_WINDOW")

    days = _days_since(events, grievance.current_stage)
    if days is None:
        # Fall back to days since status_updated_at
        delta = utcnow() - as_utc(grievance.status_updated_at)
        days = delta.total_seconds() / 86400

    # No point warning if a response already came in
    has_response = any(
        e.event_type.value in {"RESPONSE_RECEIVED", "RESOLVED", "FURTHER_ACTION"}
        for e in events
    )
    if has_response:
        return

    stage_event = _get_stage_event(events, grievance.current_stage)

    if days >= warning_days:
        event_service.create_warning_event(
            db, grievance, WarningType.POTENTIAL_DELAY,
            rule_id=rule_id,
            reason=(
                f"No response has been recorded since the grievance entered "
                f"{stage_key.replace('_', ' ').title()} ({int(days)} day(s) ago). "
                f"(Demo monitoring window: {warning_days} days.)"
            ),
            based_on_event_id=stage_event.id if stage_event else None,
        )
    elif days >= reminder_days:
        event_service.create_warning_event(
            db, grievance, WarningType.FOLLOW_UP_DUE,
            rule_id=rule_id + "_REMINDER",
            reason=(
                f"No response recorded after {int(days)} day(s). "
                f"A follow-up may be appropriate. (Demo reminder: {reminder_days} days.)"
            ),
            based_on_event_id=stage_event.id if stage_event else None,
        )


# ── Rule 3: No activity on FURTHER_ACTION ─────────────────────────────────────

def rule_further_action_stalled(db: Session, grievance: Grievance, events: list[GrievanceEvent]) -> None:
    """Warn if a grievance has been in FURTHER_ACTION without any progress."""
    if grievance.current_stage != GrievanceStage.FURTHER_ACTION:
        return

    cfg = _RULES.get("FURTHER_ACTION", {})
    warning_days = cfg.get("warning_after_days", 7)
    rule_id = cfg.get("rule_id", "DEMO_FURTHER_ACTION_WINDOW")

    days = _days_since(events, GrievanceStage.FURTHER_ACTION)
    if days is None:
        delta = utcnow() - as_utc(grievance.status_updated_at)
        days = delta.total_seconds() / 86400

    if days >= warning_days:
        fa_event = _get_stage_event(events, GrievanceStage.FURTHER_ACTION)
        event_service.create_warning_event(
            db, grievance, WarningType.NO_RECENT_UPDATE,
            rule_id=rule_id,
            reason=(
                f"The grievance has been in Further Action for {int(days)} day(s) with no resolution recorded. "
                f"(Demo window: {warning_days} days.)"
            ),
            based_on_event_id=fa_event.id if fa_event else None,
        )


# ── Rule 4: Missing acknowledgement document ───────────────────────────────────

def rule_missing_acknowledgement_document(db: Session, grievance: Grievance, events: list[GrievanceEvent]) -> None:
    """Flag when the grievance is past FILED but no acknowledgement document has been uploaded."""
    terminal = {GrievanceStage.RESOLVED}
    if grievance.current_stage in terminal:
        return
    if grievance.current_stage == GrievanceStage.FILED:
        return  # Too early to require it

    has_ack_doc = any(
        doc.document_type == DocumentType.ACKNOWLEDGEMENT
        for doc in grievance.documents
    )
    if has_ack_doc:
        return

    event_service.create_warning_event(
        db, grievance, WarningType.MISSING_INFORMATION,
        rule_id="DEMO_MISSING_ACK_DOC",
        reason=(
            "No acknowledgement document has been uploaded. Uploading it may strengthen your grievance record."
        ),
    )


# ── Rule 5: Response received but no closure for too long ────────────────────

def rule_response_received_no_closure(db: Session, grievance: Grievance, events: list[GrievanceEvent]) -> None:
    """Warn if a response was received but the case hasn't been closed within the monitoring window."""
    if grievance.current_stage != GrievanceStage.RESPONSE_RECEIVED:
        return

    cfg = _RULES.get("RESPONSE_RECEIVED", {})
    warning_days = cfg.get("warning_after_days", 10)
    rule_id = cfg.get("rule_id", "DEMO_RESPONSE_RECEIVED_WINDOW")

    days = _days_since(events, GrievanceStage.RESPONSE_RECEIVED)
    if days is None:
        delta = utcnow() - as_utc(grievance.status_updated_at)
        days = delta.total_seconds() / 86400

    if days >= warning_days:
        rr_event = _get_stage_event(events, GrievanceStage.RESPONSE_RECEIVED)
        event_service.create_warning_event(
            db, grievance, WarningType.NO_RECENT_UPDATE,
            rule_id=rule_id,
            reason=(
                f"A response was recorded {int(days)} day(s) ago but the case has not been marked resolved. "
                f"You may want to review the response and update the status. (Demo window: {warning_days} days.)"
            ),
            based_on_event_id=rr_event.id if rr_event else None,
        )


# ── Registry ───────────────────────────────────────────────────────────────────

ALL_RULES = [
    rule_filed_no_acknowledgement,
    rule_awaiting_response_window,
    rule_further_action_stalled,
    rule_missing_acknowledgement_document,
    rule_response_received_no_closure,
]
