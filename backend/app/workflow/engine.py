"""Workflow engine – Person 3.

Entry point for the rule-based grievance monitoring scheduler.
Import `run_all_checks(db)` to evaluate every active grievance
against the rules in rules.py and fire warnings via
`services.event_service.create_warning_event`.
"""
from sqlalchemy.orm import Session


def run_all_checks(db: Session) -> None:  # pragma: no cover
    """Evaluate all active grievances.  Implement in Person 3's sprint."""
    raise NotImplementedError("Workflow engine not yet implemented (Person 3).")
