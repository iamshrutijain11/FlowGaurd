"""Workflow engine — evaluates ALL active grievances against the rules in rules.py.

Public API:
    run_all_checks(db)                — evaluate every non-resolved grievance
    evaluate_grievance(db, grievance) — evaluate one grievance and return a result dict

This is the scheduler entry point. Person 4 / main.py calls run_all_checks(db)
periodically via APScheduler.

IMPORTANT: This engine produces FlowGuard *observations* only.
It does NOT make legal conclusions, assign blame, or determine regulatory violations.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models.enums import ActionType, GrievanceStage
from app.services import event_service, grievance_service
from app.workflow.rules import ALL_RULES

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.grievance import Grievance

logger = logging.getLogger("flowguard.workflow.engine")


def _determine_next_action(grievance: Grievance, warnings) -> str:
    """Deterministically choose an action category based on stage and warnings."""
    stage = grievance.current_stage

    if stage == GrievanceStage.RESOLVED:
        return ActionType.NO_ACTION.value

    if stage == GrievanceStage.FURTHER_ACTION:
        return ActionType.FURTHER_ACTION_AVAILABLE.value

    if stage == GrievanceStage.RESPONSE_RECEIVED:
        return ActionType.REVIEW_DOCUMENTS.value

    # FILED, ACKNOWLEDGED, AWAITING_RESPONSE with a warning → suggest follow-up
    if warnings:
        return ActionType.FOLLOW_UP.value

    return ActionType.NO_ACTION.value


def evaluate_grievance(db: Session, grievance: Grievance) -> dict:
    """Run all rules against one grievance and return a structured result.

    Returns:
        {
            "grievance_id": str,
            "current_stage": str,
            "warnings": [WarningOut, ...],   # newly recorded + existing active warnings
            "recommended_system_action": str  # ActionType value
        }
    """
    events = event_service.list_events(db, grievance.id)

    # Run each rule (each is idempotent — won't duplicate existing warnings)
    errors = []
    for rule in ALL_RULES:
        try:
            rule(db, grievance, events)
        except Exception as exc:  # pragma: no cover
            logger.exception("Rule %s failed for grievance %s: %s", rule.__name__, grievance.id, exc)
            errors.append(str(exc))

    # Reload events (rules may have added new ones)
    events = event_service.list_events(db, grievance.id)
    active_warning = event_service.get_active_warning(grievance, events)
    warnings = [active_warning] if active_warning else []

    action = _determine_next_action(grievance, warnings)

    return {
        "grievance_id": str(grievance.id),
        "current_stage": grievance.current_stage.value,
        "warnings": warnings,
        "recommended_system_action": action,
        "rule_errors": errors,
    }


def run_all_checks(db: Session) -> dict:
    """Evaluate every active (non-RESOLVED) grievance.

    Called by APScheduler. Returns a summary dict for logging.
    """
    grievances = grievance_service.get_active_grievances(db)
    results = {"evaluated": 0, "warnings_active": 0, "errors": 0}

    for grievance in grievances:
        try:
            result = evaluate_grievance(db, grievance)
            results["evaluated"] += 1
            results["warnings_active"] += len(result["warnings"])
            results["errors"] += len(result.get("rule_errors", []))
        except Exception as exc:  # pragma: no cover
            logger.exception("Engine failed for grievance %s: %s", grievance.id, exc)
            results["errors"] += 1

    logger.info(
        "Grievance check complete: %d evaluated, %d with active warnings, %d errors.",
        results["evaluated"], results["warnings_active"], results["errors"]
    )
    return results
