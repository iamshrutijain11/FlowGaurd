"""State machine – Person 3.

Expose `validate_transition(from_stage: str, to_stage: str) -> bool`.
The PATCH /grievances/{id} route imports this automatically when the
file is present (see app/services/grievance_service.py::_check_transition).

Until this module is filled in, any valid stage value is accepted.
"""


TRANSITIONS: dict[str, list[str]] = {
    # from_stage -> list of allowed to_stages
    "FILED":              ["ACKNOWLEDGED"],
    "ACKNOWLEDGED":       ["AWAITING_RESPONSE"],
    "AWAITING_RESPONSE":  ["RESPONSE_RECEIVED", "FURTHER_ACTION", "RESOLVED"],
    "RESPONSE_RECEIVED":  ["RESOLVED", "FURTHER_ACTION"],
    "FURTHER_ACTION":     ["RESOLVED"],
    "RESOLVED":           [],
}


def validate_transition(from_stage: str, to_stage: str) -> bool:
    """Return True if the stage change is allowed by the state machine."""
    return to_stage in TRANSITIONS.get(from_stage, [])
