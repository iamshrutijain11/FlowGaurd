import io
from datetime import datetime, timezone

from app.db.seed import DEMO_COMPLAINT_ID, DEMO_EMAIL, DEMO_PASSWORD, seed_demo_data
from app.models.enums import GrievanceStage, WarningType
from app.models.grievance import Grievance
from app.services import event_service
from tests.conftest import GRIEVANCE, register_and_login

PDF = b"%PDF-1.4\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ------------------------------------------------------------------ auth
def test_register_login_me(client):
    h = register_and_login(client)
    me = client.get("/api/v1/auth/me", headers=h).json()
    assert me["success"] and me["data"]["email"] == "investor@flowguard.app"
    assert "hashed_password" not in me["data"]


def test_register_accepts_full_name_alias(client):
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Asha", "email": "asha@flowguard.app", "password": "Passw0rd!x", "preferred_language": "hi"})
    assert r.status_code == 201 and r.json()["data"]["preferred_language"] == "hi"


def test_duplicate_email_and_bad_login(client, auth):
    r = client.post("/api/v1/auth/register", json={"name": "x", "email": "investor@flowguard.app", "password": "Passw0rd!x"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    r = client.post("/api/v1/auth/login", json={"email": "investor@flowguard.app", "password": "wrong-pass"})
    assert r.status_code == 401 and r.json() == {
        "success": False, "error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."}}


def test_protected_routes_need_token(client):
    r = client.get("/api/v1/grievances")
    assert r.status_code == 401 and r.json()["success"] is False
    r = client.get("/api/v1/grievances", headers={"Authorization": "Bearer garbage"})
    assert r.json()["error"]["code"] == "INVALID_TOKEN"


def test_validation_error_envelope(client, auth):
    r = client.post("/api/v1/grievances", json={"entity_name": "x"}, headers=auth)
    body = r.json()
    assert r.status_code == 422 and body["error"]["code"] == "VALIDATION_ERROR" and body["error"]["details"]


# ------------------------------------------------------------------ grievances
def test_create_builds_timeline(client, auth, grievance):
    assert grievance["current_stage"] == "FILED" and grievance["warning"] is None
    ev = client.get(f"/api/v1/grievances/{grievance['id']}/events", headers=auth).json()["data"]
    assert [e["event_type"] for e in ev] == ["FILED"]


def test_create_with_known_status_backfills(client, auth):
    body = {**GRIEVANCE, "complaint_id": "CMP-X", "acknowledgement_date": "2026-09-20T12:00:00Z",
            "current_stage": "AWAITING_RESPONSE"}
    g = client.post("/api/v1/grievances", json=body, headers=auth).json()["data"]
    ev = client.get(f"/api/v1/grievances/{g['id']}/events", headers=auth).json()["data"]
    assert [e["event_type"] for e in ev] == ["FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE"]
    assert g["current_stage"] == "AWAITING_RESPONSE"


def test_duplicate_complaint_id_and_bad_dates(client, auth, grievance):
    r = client.post("/api/v1/grievances", json=GRIEVANCE, headers=auth)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_COMPLAINT_ID"
    bad = {**GRIEVANCE, "complaint_id": "Z", "acknowledgement_date": "2026-09-01T00:00:00Z"}
    assert client.post("/api/v1/grievances", json=bad, headers=auth).status_code == 422


def test_ownership_isolated(client, grievance):
    other = register_and_login(client, email="other@flowguard.app")
    gid = grievance["id"]
    assert client.get("/api/v1/grievances", headers=other).json()["data"] == []
    for path in ("", "/events", "/documents", "/next-action", "/explanation"):
        r = client.get(f"/api/v1/grievances/{gid}{path}", headers=other)
        assert r.status_code == 404 and r.json()["error"]["code"] == "GRIEVANCE_NOT_FOUND"
    assert client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "ACKNOWLEDGED"}, headers=other).status_code == 404


def test_patch_stage_creates_event_and_notification(client, auth, grievance):
    gid = grievance["id"]
    r = client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "ACKNOWLEDGED"}, headers=auth)
    assert r.status_code == 200 and r.json()["data"]["current_stage"] == "ACKNOWLEDGED"
    ev = client.get(f"/api/v1/grievances/{gid}/events", headers=auth).json()["data"]
    assert ev[-1]["event_type"] == "ACKNOWLEDGED" and ev[-1]["metadata"]["previous_stage"] == "FILED"
    notes = client.get("/api/v1/notifications", headers=auth).json()["data"]
    assert notes[0]["notification_type"] == "STATUS_CHANGED" and notes[0]["read"] is False
    assert client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "NOPE"}, headers=auth).status_code == 422
    assert client.patch(f"/api/v1/grievances/{gid}", json={}, headers=auth).json()["error"]["code"] == "NO_CHANGES"


def test_patch_details_is_recorded_in_history(client, auth, grievance):
    gid = grievance["id"]
    client.patch(f"/api/v1/grievances/{gid}", json={"entity_name": "Renamed Ltd"}, headers=auth)
    ev = client.get(f"/api/v1/grievances/{gid}/events", headers=auth).json()["data"]
    assert ev[-1]["event_type"] == "DETAILS_UPDATED"
    assert ev[-1]["metadata"]["changes"]["entity_name"]["old"] == "Demo Brokerage Pvt Ltd"


def test_delete_not_exposed(client, auth, grievance):
    assert client.delete(f"/api/v1/grievances/{grievance['id']}", headers=auth).status_code == 405


# ------------------------------------------------------------------ events
def test_user_events_restricted(client, auth, grievance):
    url = f"/api/v1/grievances/{grievance['id']}/events"
    ok = client.post(url, json={"event_type": "NOTE_ADDED", "description": "Called helpdesk"}, headers=auth)
    assert ok.status_code == 201 and ok.json()["data"]["source"] == "USER"
    bad = client.post(url, json={"event_type": "POTENTIAL_DELAY", "description": "fake"}, headers=auth)
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "EVENT_TYPE_NOT_ALLOWED"


# ------------------------------------------------------------------ warnings / dashboard
def test_warning_is_separate_from_stage_and_counts(client, auth, db, grievance):
    gid = grievance["id"]
    client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "ACKNOWLEDGED"}, headers=auth)
    client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "AWAITING_RESPONSE"}, headers=auth)
    assert client.get("/api/v1/dashboard/summary", headers=auth).json()["data"] == {
        "active": 1, "on_track": 1, "potentially_delayed": 0, "resolved": 0}

    import uuid
    g = db.get(Grievance, uuid.UUID(gid))
    args = dict(rule_id="DEMO_AWAITING_RESPONSE_WINDOW", reason="No response event has been recorded.")
    first = event_service.create_warning_event(db, g, WarningType.POTENTIAL_DELAY, **args)
    second = event_service.create_warning_event(db, g, WarningType.POTENTIAL_DELAY, **args)
    assert first.id == second.id  # duplicate prevented

    out = client.get(f"/api/v1/grievances/{gid}", headers=auth).json()["data"]
    assert out["current_stage"] == "AWAITING_RESPONSE"
    assert out["warning"]["type"] == "POTENTIAL_DELAY" and out["warning"]["rule"] == "DEMO_AWAITING_RESPONSE_WINDOW"
    assert client.get("/api/v1/dashboard/summary", headers=auth).json()["data"]["potentially_delayed"] == 1
    action = client.get(f"/api/v1/grievances/{gid}/next-action", headers=auth).json()["data"]
    assert action["type"] == "FOLLOW_UP" and action["official_source"] is None

    # moving stage clears the warning; resolving counts as resolved
    client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "RESPONSE_RECEIVED"}, headers=auth)
    assert client.get(f"/api/v1/grievances/{gid}", headers=auth).json()["data"]["warning"] is None
    client.patch(f"/api/v1/grievances/{gid}", json={"current_stage": "RESOLVED"}, headers=auth)
    s = client.get("/api/v1/dashboard/summary", headers=auth).json()["data"]
    assert s == {"active": 0, "on_track": 0, "potentially_delayed": 0, "resolved": 1}


def test_explanation_shape(client, auth, grievance):
    d = client.get(f"/api/v1/grievances/{grievance['id']}/explanation", headers=auth).json()["data"]
    for key in ("current_situation", "timeline_summary", "warning_explanation", "missing_information",
                "next_step_summary", "generated_at"):
        assert key in d


# ------------------------------------------------------------------ documents
def _upload(client, auth, gid, name, content, dtype="ACKNOWLEDGEMENT"):
    return client.post(
        f"/api/v1/grievances/{gid}/documents", headers=auth,
        files={"file": (name, io.BytesIO(content))}, data={"document_type": dtype})


def test_document_upload_and_download(client, auth, grievance):
    gid = grievance["id"]
    r = _upload(client, auth, gid, "ack.pdf", PDF)
    assert r.status_code == 201
    doc = r.json()["data"]
    assert doc["extraction_status"] == "PENDING" and doc["document_type"] == "ACKNOWLEDGEMENT"
    assert "storage_path" not in doc
    assert _upload(client, auth, gid, "shot.png", PNG, "SCREENSHOT").status_code == 201
    listed = client.get(f"/api/v1/grievances/{gid}/documents", headers=auth).json()["data"]
    assert len(listed) == 2
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth).json()["data"]["file_name"] == "ack.pdf"
    dl = client.get(doc["download_url"], headers=auth)
    assert dl.status_code == 200 and dl.content == PDF
    ev = client.get(f"/api/v1/grievances/{gid}/events", headers=auth).json()["data"]
    assert any(e["event_type"] == "DOCUMENT_UPLOADED" for e in ev)


def test_document_validation_and_ownership(client, auth, grievance):
    gid = grievance["id"]
    assert _upload(client, auth, gid, "evil.exe", b"MZ").json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert _upload(client, auth, gid, "fake.pdf", b"not a pdf").status_code == 415
    assert _upload(client, auth, gid, "empty.pdf", b"").json()["error"]["code"] == "EMPTY_FILE"
    doc = _upload(client, auth, gid, "ack.pdf", PDF).json()["data"]
    other = register_and_login(client, email="other@flowguard.app")
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=other).status_code == 404
    assert client.get(doc["download_url"], headers=other).status_code == 404


# ------------------------------------------------------------------ notifications
def test_notification_mark_read(client, auth, grievance):
    client.patch(f"/api/v1/grievances/{grievance['id']}", json={"current_stage": "ACKNOWLEDGED"}, headers=auth)
    n = client.get("/api/v1/notifications", headers=auth).json()["data"][0]
    r = client.patch(f"/api/v1/notifications/{n['id']}/read", headers=auth)
    assert r.json()["data"]["read"] is True
    other = register_and_login(client, email="other@flowguard.app")
    assert client.patch(f"/api/v1/notifications/{n['id']}/read", headers=other).status_code == 404


# ------------------------------------------------------------------ seed
def test_seed_is_idempotent_and_matches_contract(client, db):
    seed_demo_data(db)
    seed_demo_data(db)
    r = client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    h = {"Authorization": f"Bearer {r.json()['data']['access_token']}"}
    items = client.get("/api/v1/grievances", headers=h).json()["data"]
    assert len(items) == 1
    g = items[0]
    assert g["complaint_id"] == DEMO_COMPLAINT_ID and g["current_stage"] == GrievanceStage.AWAITING_RESPONSE.value
    assert g["warning"] is None
    ev = client.get(f"/api/v1/grievances/{g['id']}/events", headers=h).json()["data"]
    assert [e["event_type"] for e in ev] == ["FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE"]
    assert datetime.fromisoformat(ev[0]["event_time"].replace("Z", "+00:00")) == datetime(2026, 9, 20, 10, tzinfo=timezone.utc)
    docs = client.get(f"/api/v1/grievances/{g['id']}/documents", headers=h).json()["data"]
    assert docs[0]["document_type"] == "ACKNOWLEDGEMENT"
