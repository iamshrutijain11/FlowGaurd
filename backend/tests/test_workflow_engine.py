"""Person 3: workflow engine tests (scenarios A-G + state machine).

Builds cases through the real API, then moves event timestamps back in time,
so the engine's real clock sees the case as N days old.
"""
import uuid
from datetime import timedelta

from app.models.enums import EventSource, EventType
from app.services import event_service, grievance_service
from app.utils.time import utcnow
from app.workflow.engine import evaluate_grievance, run_all_checks
from app.workflow.state_machine import validate_transition
from tests.conftest import GRIEVANCE


def build_case(client, auth, db, stage, days, cid="CMP-T-001"):
    """Create a grievance in `stage` that entered that stage `days` days ago."""
    payload = {**GRIEVANCE, "complaint_id": cid, "current_stage": stage}
    r = client.post("/api/v1/grievances", json=payload, headers=auth)
    assert r.status_code == 201, r.text
    g = grievance_service.get_grievance(db, uuid.UUID(r.json()["data"]["id"]))

    now = utcnow()
    for e in event_service.list_events(db, g.id):
        if e.event_type.value == stage:
            e.event_time = now - timedelta(days=days)
        else:
            e.event_time = now - timedelta(days=days + 1)
    g.status_updated_at = now - timedelta(days=days)
    db.commit()
    return g


def count_events(db, g, event_type):
    return len([e for e in event_service.list_events(db, g.id) if e.event_type.value == event_type])


def stage_event(db, g, stage):
    return next(e for e in event_service.list_events(db, g.id) if e.event_type.value == stage)


def add_dependency_note(db, g, marker, days_ago):
    event_service.create_event(
        db, g.id, EventType.NOTE_ADDED, marker,
        source=EventSource.USER,
        event_time=utcnow() - timedelta(days=days_ago),
        metadata={"dependency": marker},
    )


# ---------- Scenario A: normal case ----------
def test_a_normal_case_no_delay(client, auth, db):
    g = build_case(client, auth, db, "RESPONSE_RECEIVED", days=1)
    result = evaluate_grievance(db, g)
    assert count_events(db, g, "POTENTIAL_DELAY") == 0
    assert all(w.type != "POTENTIAL_DELAY" for w in result["warnings"])


# ---------- Scenario B: delayed demo case ----------
def test_b_delayed_case_potential_delay(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=6)
    result = evaluate_grievance(db, g)

    assert result["current_stage"] == "AWAITING_RESPONSE"
    assert result["recommended_system_action"] == "FOLLOW_UP"
    warning = result["warnings"][0]
    assert warning.type == "POTENTIAL_DELAY"
    assert warning.rule == "DEMO_AWAITING_RESPONSE_WINDOW"
    assert warning.reason  # explainable
    assert warning.based_on_event == str(stage_event(db, g, "AWAITING_RESPONSE").id)


# ---------- Scenario C: recently awaiting ----------
def test_c_recent_awaiting_no_delay(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=1)
    evaluate_grievance(db, g)
    assert count_events(db, g, "POTENTIAL_DELAY") == 0
    assert count_events(db, g, "FOLLOW_UP_DUE") == 0


def test_c2_reminder_before_warning(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=4)
    evaluate_grievance(db, g)
    assert count_events(db, g, "FOLLOW_UP_DUE") == 1
    assert count_events(db, g, "POTENTIAL_DELAY") == 0


# ---------- Scenario D: missing documentation ----------
def test_d_missing_acknowledgement_document(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=1)
    result = evaluate_grievance(db, g)
    assert count_events(db, g, "MISSING_INFORMATION") == 1
    assert result["warnings"][0].type == "MISSING_INFORMATION"


# ---------- Scenario E: resolved ----------
def test_e_resolved_case_no_warning(client, auth, db):
    g = build_case(client, auth, db, "RESOLVED", days=1)
    result = evaluate_grievance(db, g)
    assert result["warnings"] == []
    assert result["recommended_system_action"] == "NO_ACTION"
    assert count_events(db, g, "POTENTIAL_DELAY") == 0


# ---------- Scenario F: duplicate scheduler execution ----------
def test_f_running_twice_creates_one_warning(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=6)
    evaluate_grievance(db, g)
    evaluate_grievance(db, g)
    assert count_events(db, g, "POTENTIAL_DELAY") == 1


def test_f2_run_all_checks_is_idempotent(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=6)
    first = run_all_checks(db)
    run_all_checks(db)
    assert first["evaluated"] >= 1
    assert first["warnings_active"] >= 1
    assert count_events(db, g, "POTENTIAL_DELAY") == 1


# ---------- Scenario G: waiting on the investor ----------
def test_g1_user_dependency_not_blamed_on_intermediary(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=6)
    add_dependency_note(db, g, "USER_INFORMATION_REQUESTED", days_ago=4)
    result = evaluate_grievance(db, g)

    assert count_events(db, g, "POTENTIAL_DELAY") == 0
    assert result["delay_attribution"] == "UNKNOWN"
    assert result["blocking_dependency"] == "USER_DOCUMENT_REQUIRED"


def test_g2_delay_detection_resumes_after_user_provides_info(client, auth, db):
    g = build_case(client, auth, db, "AWAITING_RESPONSE", days=6)
    add_dependency_note(db, g, "USER_INFORMATION_REQUESTED", days_ago=4)
    add_dependency_note(db, g, "USER_INFORMATION_PROVIDED", days_ago=1)
    result = evaluate_grievance(db, g)

    assert result["delay_attribution"] is None
    assert count_events(db, g, "POTENTIAL_DELAY") == 1


# ---------- State machine ----------
def test_state_machine_allowed_and_blocked():
    assert validate_transition("FILED", "ACKNOWLEDGED")
    assert validate_transition("ACKNOWLEDGED", "AWAITING_RESPONSE")
    assert validate_transition("RESPONSE_RECEIVED", "FURTHER_ACTION")
    assert not validate_transition("FILED", "RESOLVED")
    assert not validate_transition("FILED", "AWAITING_RESPONSE")
    assert not validate_transition("RESOLVED", "FILED")