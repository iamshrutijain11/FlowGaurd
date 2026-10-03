"""
test_integration_demo.py - Integration Test Suite for FlowGuard (Person 4).

Tests the full Person 4 pipeline against the real backend API using shared demo case CMP-2026-DEMO-001:
1. Document Extraction (AI extraction with value/confidence objects & heuristic fallback).
2. Evidence & Timeline Helper (timeline ordering, suggested documents, completeness).
3. Verified Guidance Loader (official SEBI SCORES / SMART ODR routes, demo disclaimers).
4. Grievance Summarizer (controlled context assembly, 5-key JSON schema, anti-hallucination).
5. Notification Service (in-app, simulated email, simulated SMS, dispatch).
6. Real API: Seed data & Authentication for demo user.
7. Real API: Workflow delay detection & Notification generation.
8. Real API: Plain-language explanation via GET /api/v1/grievances/{id}/explanation.
9. Real API: Verified next-action guidance via GET /api/v1/grievances/{id}/next-action.
10. Real API: Real document upload & extraction via POST /api/v1/grievances/{id}/documents.
11. Real API: Full End-to-End Walkthrough on CMP-2026-DEMO-001.
"""

import io
import json
import unittest
import uuid
from typing import Any, Dict

from fastapi.testclient import TestClient

import app.models
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.seed import seed_demo_data, DEMO_EMAIL, DEMO_PASSWORD, DEMO_COMPLAINT_ID
from app.main import app
from app.models.grievance import Grievance
from app.workflow.engine import evaluate_grievance
from app.ai.extraction import (
    ExtractedField,
    ExtractedGrievanceData,
    extract_grievance_data,
    fallback_heuristic_extraction,
    DEMO_DOCUMENT_TEXT,
)
from app.ai.evidence_helper import (
    STAGE_DOCUMENT_SUGGESTIONS,
    build_timeline,
    build_checklist,
    build_evidence_report,
    get_demo_evidence_report,
)
from app.ai.guidance_loader import (
    VALID_STAGES,
    get_guidance,
    get_entity_guidance,
    get_escalation_matrix,
    load_all_guidance,
    normalize_entity_type,
    normalize_stage,
)
from app.ai.summarizer import (
    ControlledContext,
    GrievanceSummaryResponse,
    build_controlled_context,
    get_fallback_summary,
    summarize_grievance,
    get_demo_case_context,
)
from app.notifications.notifications import (
    NotificationItem,
    NotificationService,
    NotificationSeverity,
    NotificationType,
    create_stage_transition_notification,
    create_delay_warning_notification,
    create_evidence_reminder_notification,
    create_next_action_notification,
    create_warning_notification_for_grievance,
    format_email_demo,
    format_sms_demo,
    get_demo_notifications,
)


class TestFlowGuardPerson4Integration(unittest.TestCase):
    """Full integration test suite for Person 4 deliverables running against the real API."""

    @classmethod
    def setUpClass(cls):
        cls.demo_complaint_id = DEMO_COMPLAINT_ID
        cls.demo_entity_name = "Demo Brokerage Pvt Ltd"
        cls.demo_stage = "AWAITING_RESPONSE"
        cls.demo_warning = "response_window_exceeded"

    def setUp(self):
        """Prepare fresh database and seeded demo case before each test."""
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.client = TestClient(app)
        with SessionLocal() as db:
            seed_demo_data(db)

    def _login_demo_user(self) -> Dict[str, str]:
        """Logs in the demo user and returns authorization headers."""
        resp = self.client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        self.assertEqual(resp.status_code, 200, f"Login failed: {resp.text}")
        token = resp.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _get_demo_grievance(self, auth: Dict[str, str]) -> Dict[str, Any]:
        """Fetches the shared demo case CMP-2026-DEMO-001 for the demo user."""
        resp = self.client.get("/api/v1/grievances", headers=auth)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()["data"]
        matching = [g for g in items if g["complaint_id"] == self.demo_complaint_id]
        self.assertTrue(len(matching) > 0, f"Demo grievance {self.demo_complaint_id} not found in user list")
        return matching[0]

    # ------------------------------------------------------------------------
    # 1. Document Extraction Tests (Standalone Schema & Fallback)
    # ------------------------------------------------------------------------
    def test_01_document_extraction_schema_and_fallback(self):
        """Verify extraction returns {value, confidence} objects marked as suggestions."""
        data = fallback_heuristic_extraction(DEMO_DOCUMENT_TEXT)
        self.assertIsInstance(data, dict)

        for field in ["complaint_id", "entity_name", "submission_date", "issue_description", "detected_stage"]:
            self.assertIn(field, data)
            self.assertIn("value", data[field])
            self.assertIn("confidence", data[field])
            self.assertIsInstance(data[field]["confidence"], (int, float))
            self.assertGreaterEqual(data[field]["confidence"], 0.0)
            self.assertLessEqual(data[field]["confidence"], 1.0)

        self.assertEqual(data["complaint_id"]["value"], self.demo_complaint_id)
        self.assertEqual(data["entity_name"]["value"], self.demo_entity_name)
        self.assertEqual(data["submission_date"]["value"], "2026-09-20")
        self.assertEqual(data["detected_stage"]["value"], "ACKNOWLEDGED")
        self.assertTrue(data.get("requires_user_confirmation"))
        self.assertEqual(data.get("status"), "SUGGESTION_PENDING_CONFIRMATION")

        validated = ExtractedGrievanceData(**data)
        self.assertEqual(validated.complaint_id.value, self.demo_complaint_id)

    # ------------------------------------------------------------------------
    # 2. Evidence & Timeline Helper Tests
    # ------------------------------------------------------------------------
    def test_02_evidence_helper_stages_and_suggestions(self):
        """Verify evidence helper uses exact 6 stages and non-mandatory suggestion wording."""
        expected_stages = [
            "FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE",
            "RESPONSE_RECEIVED", "RESOLVED", "FURTHER_ACTION"
        ]
        self.assertEqual(sorted(list(STAGE_DOCUMENT_SUGGESTIONS.keys())), sorted(expected_stages))

        report = get_demo_evidence_report()
        self.assertEqual(report["complaint_id"], self.demo_complaint_id)
        self.assertEqual(report["current_stage"], self.demo_stage)
        self.assertEqual(len(report["timeline"]), 3)
        self.assertEqual(report["total_suggested"], 3)
        self.assertEqual(report["total_uploaded"], 1)
        self.assertEqual(report["total_missing"], 2)
        self.assertEqual(report["completeness_pct"], 33.3)

        for item in report["checklist"]:
            self.assertIn("may be useful for your grievance record", item["guidance_note"].lower())
            self.assertNotIn("legally required", item["guidance_note"].lower())

    # ------------------------------------------------------------------------
    # 3. Verified Guidance Loader Tests
    # ------------------------------------------------------------------------
    def test_03_guidance_loader_official_paths_and_disclaimer(self):
        """Verify verified guidance loader retrieves official portals and demo disclaimers."""
        guidance = get_guidance(
            entity_type=self.demo_entity_name,
            stage=self.demo_stage,
            warning_type=self.demo_warning
        )

        self.assertEqual(guidance["entity_type"], "stock_broker")
        self.assertEqual(guidance["stage"], "AWAITING_RESPONSE")
        self.assertEqual(guidance["official_portal"], "https://scores.sebi.gov.in")
        self.assertIn("SEBI SCORES 2.0", guidance["escalation_path"])
        self.assertIn("demo configuration", guidance["disclaimer"].lower())
        self.assertIn("warning_guidance", guidance)

        matrix = get_escalation_matrix()
        self.assertEqual(len(matrix.get("tiers", [])), 4)

    # ------------------------------------------------------------------------
    # 4. Grievance Summarizer Tests
    # ------------------------------------------------------------------------
    def test_04_summarizer_controlled_context_and_schema(self):
        """Verify controlled context and 5-key summary schema adherence."""
        context = get_demo_case_context()
        for key in ["grievance", "events", "workflow_result", "documents", "verified_guidance"]:
            self.assertIn(key, context)

        fallback = get_fallback_summary(context)
        for key in ["current_situation", "what_happened", "possible_missing_information", "warning_explanation", "next_step_summary"]:
            self.assertIn(key, fallback)
            self.assertIsInstance(fallback[key], str)
            self.assertGreater(len(fallback[key]), 5)

        self.assertIn(self.demo_complaint_id, fallback["current_situation"])
        self.assertIn("demo configuration", fallback["warning_explanation"].lower())
        self.assertIn("https://scores.sebi.gov.in", fallback["next_step_summary"])

    # ------------------------------------------------------------------------
    # 5. Notification Service Tests
    # ------------------------------------------------------------------------
    def test_05_notifications_generation_and_channels(self):
        """Verify in-app, email, and SMS notification generation and dispatch."""
        notifications_data = get_demo_notifications()
        self.assertEqual(notifications_data["complaint_id"], self.demo_complaint_id)
        self.assertEqual(notifications_data["total_notifications"], 5)

        in_app = notifications_data["in_app_notifications"]
        types = [n["type"] for n in in_app]
        self.assertIn("STAGE_TRANSITION", types)
        self.assertIn("DELAY_WARNING", types)
        self.assertIn("EVIDENCE_REMINDER", types)
        self.assertIn("NEXT_ACTION_GUIDANCE", types)

        warn_notif = next(n for n in in_app if n["type"] == "DELAY_WARNING")
        self.assertEqual(warn_notif["severity"], "WARNING")
        self.assertIn("demo configuration", warn_notif["message"].lower())

        email = notifications_data["simulated_email"]
        self.assertEqual(email["channel"], "EMAIL_DEMO")
        self.assertIn(self.demo_complaint_id, email["body"])

        sms = notifications_data["simulated_sms"]
        self.assertEqual(sms["channel"], "SMS_DEMO")
        self.assertIn(self.demo_complaint_id, sms["sms_text"])

    # ------------------------------------------------------------------------
    # 6. Real API: Seed Data & Auth Verification
    # ------------------------------------------------------------------------
    def test_06_real_api_auth_and_demo_seed(self):
        """Verify real API authentication and seeded CMP-2026-DEMO-001 record."""
        auth = self._login_demo_user()
        g = self._get_demo_grievance(auth)

        self.assertEqual(g["complaint_id"], self.demo_complaint_id)
        self.assertEqual(g["current_stage"], "AWAITING_RESPONSE")
        self.assertEqual(g["entity_name"], self.demo_entity_name)

        # Check seeded timeline events via real endpoint
        ev_resp = self.client.get(f"/api/v1/grievances/{g['id']}/events", headers=auth)
        self.assertEqual(ev_resp.status_code, 200)
        events = ev_resp.json()["data"]
        self.assertEqual([e["event_type"] for e in events], ["FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE"])

    # ------------------------------------------------------------------------
    # 7. Real API: Workflow Warning & Notification Integration
    # ------------------------------------------------------------------------
    def test_07_real_api_workflow_warning_and_notification(self):
        """Verify workflow engine generates POTENTIAL_DELAY warning and creates a notification."""
        auth = self._login_demo_user()
        g = self._get_demo_grievance(auth)

        # Run workflow engine evaluation against seeded grievance
        with SessionLocal() as db:
            g_obj = db.get(Grievance, uuid.UUID(g["id"]))
            eval_result = evaluate_grievance(db, g_obj)
            self.assertTrue(len(eval_result["warnings"]) > 0)
            self.assertEqual(eval_result["warnings"][0].type, "POTENTIAL_DELAY")

        # Verify grievance endpoint reflects the active warning
        g_updated = self.client.get(f"/api/v1/grievances/{g['id']}", headers=auth).json()["data"]
        self.assertIsNotNone(g_updated["warning"])
        self.assertEqual(g_updated["warning"]["type"], "POTENTIAL_DELAY")

        # Verify notification was generated and accessible via GET /api/v1/notifications
        notifs_resp = self.client.get("/api/v1/notifications", headers=auth)
        self.assertEqual(notifs_resp.status_code, 200)
        notifs = notifs_resp.json()["data"]
        self.assertTrue(len(notifs) > 0)

        delay_notif = next((n for n in notifs if n["notification_type"] == "POTENTIAL_DELAY"), None)
        self.assertIsNotNone(delay_notif)
        self.assertIn(self.demo_complaint_id, delay_notif["title"])
        self.assertIn("demo configuration", delay_notif["message"].lower())
        self.assertFalse(delay_notif["read"])

        # Mark read via real API endpoint
        patch_resp = self.client.patch(f"/api/v1/notifications/{delay_notif['id']}/read", headers=auth)
        self.assertEqual(patch_resp.status_code, 200)
        self.assertTrue(patch_resp.json()["data"]["read"])

    # ------------------------------------------------------------------------
    # 8. Real API: Plain-Language Explanation Endpoint
    # ------------------------------------------------------------------------
    def test_08_real_api_explanation_endpoint(self):
        """Verify GET /api/v1/grievances/{id}/explanation calls summarizer on real data."""
        auth = self._login_demo_user()
        g = self._get_demo_grievance(auth)

        # Trigger workflow evaluation to simulate active monitoring window warning
        with SessionLocal() as db:
            g_obj = db.get(Grievance, uuid.UUID(g["id"]))
            evaluate_grievance(db, g_obj)

        exp_resp = self.client.get(f"/api/v1/grievances/{g['id']}/explanation", headers=auth)
        self.assertEqual(exp_resp.status_code, 200)
        body = exp_resp.json()
        self.assertTrue(body["success"])

        data = body["data"]
        self.assertIn(self.demo_complaint_id, data["current_situation"])
        self.assertIn(self.demo_entity_name, data["current_situation"])
        self.assertIn("timeline", data["timeline_summary"].lower())
        self.assertIsNotNone(data["warning_explanation"])
        self.assertIn("demo configuration", data["warning_explanation"].lower())
        self.assertIn("scores.sebi.gov.in", data["next_step_summary"])
        self.assertFalse(data["is_placeholder"])

    # ------------------------------------------------------------------------
    # 9. Real API: Verified Next-Action Guidance Endpoint
    # ------------------------------------------------------------------------
    def test_09_real_api_next_action_guidance(self):
        """Verify GET /api/v1/grievances/{id}/next-action returns verified guidance data."""
        auth = self._login_demo_user()
        g = self._get_demo_grievance(auth)

        # Trigger workflow evaluation
        with SessionLocal() as db:
            g_obj = db.get(Grievance, uuid.UUID(g["id"]))
            evaluate_grievance(db, g_obj)

        action_resp = self.client.get(f"/api/v1/grievances/{g['id']}/next-action", headers=auth)
        self.assertEqual(action_resp.status_code, 200)
        body = action_resp.json()
        self.assertTrue(body["success"])

        data = body["data"]
        self.assertEqual(data["type"], "FOLLOW_UP")
        self.assertIn("Follow-up", data["title"])
        self.assertFalse(data["is_placeholder"])
        self.assertTrue(len(data["required_documents"]) > 0)

        # Verify official source is populated as a plain string and extra fields are flattened
        self.assertIsNotNone(data["official_source"])
        self.assertIsInstance(data["official_source"], str)
        self.assertIn("scores.sebi.gov.in", data["official_source"])
        self.assertIn("SEBI SCORES 2.0", data["official_source"])
        self.assertIn("SEBI SCORES 2.0", data["escalation_path"])
        self.assertIsInstance(data["conditions"], list)
        self.assertIsInstance(data["required_documents"], list)
        for doc_item in data["required_documents"]:
            self.assertIsInstance(doc_item, str)
        self.assertIn("demo configuration", data["disclaimer"].lower())

    # ------------------------------------------------------------------------
    # 10. Real API: Document Upload & AI Extraction
    # ------------------------------------------------------------------------
    def test_10_real_api_document_upload_and_extraction(self):
        """Verify document upload triggers extraction and stores suggestions in extracted_data."""
        auth = self._login_demo_user()
        g = self._get_demo_grievance(auth)

        # Prepare uploaded document carrying text from the demo acknowledgement
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Length " + str(len(DEMO_DOCUMENT_TEXT)).encode() + b" >>\nstream\n"
            + DEMO_DOCUMENT_TEXT.encode("utf-8")
            + b"\nendstream\nendobj\n%%EOF\n"
        )

        upload_resp = self.client.post(
            f"/api/v1/grievances/{g['id']}/documents",
            headers=auth,
            files={"file": ("acknowledgement_receipt.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"document_type": "ACKNOWLEDGEMENT"}
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc = upload_resp.json()["data"]

        self.assertEqual(doc["extraction_status"], "COMPLETED")
        self.assertIsNotNone(doc["extracted_data"])
        extracted = doc["extracted_data"]

        # Validate extracted suggestion structure
        for field in ["complaint_id", "entity_name", "submission_date", "issue_description", "detected_stage"]:
            self.assertIn(field, extracted)
            self.assertIn("value", extracted[field])
            self.assertIn("confidence", extracted[field])

        self.assertEqual(extracted["complaint_id"]["value"], self.demo_complaint_id)
        self.assertEqual(extracted["detected_stage"]["value"], "ACKNOWLEDGED")
        self.assertTrue(extracted["requires_user_confirmation"])
        self.assertEqual(extracted["status"], "SUGGESTION_PENDING_CONFIRMATION")

        # Verify listed documents include the extracted data
        list_resp = self.client.get(f"/api/v1/grievances/{g['id']}/documents", headers=auth)
        self.assertEqual(list_resp.status_code, 200)
        docs = list_resp.json()["data"]
        matching = [d for d in docs if d["id"] == doc["id"]]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["extraction_status"], "COMPLETED")

    # ------------------------------------------------------------------------
    # 11. Full End-to-End Walkthrough on CMP-2026-DEMO-001
    # ------------------------------------------------------------------------
    def test_11_real_api_end_to_end_walkthrough(self):
        """Complete integrated pipeline run against real API on CMP-2026-DEMO-001."""
        # 1. Authenticate demo user
        auth = self._login_demo_user()

        # 2. Retrieve seeded grievance
        g = self._get_demo_grievance(auth)
        gid = g["id"]
        self.assertEqual(g["complaint_id"], self.demo_complaint_id)

        # 3. Ingest supporting document & execute extraction
        doc_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Length " + str(len(DEMO_DOCUMENT_TEXT)).encode() + b" >>\nstream\n"
            + DEMO_DOCUMENT_TEXT.encode("utf-8")
            + b"\nendstream\nendobj\n%%EOF\n"
        )
        up_resp = self.client.post(
            f"/api/v1/grievances/{gid}/documents",
            headers=auth,
            files={"file": ("acknowledgement_receipt.pdf", io.BytesIO(doc_bytes), "application/pdf")},
            data={"document_type": "ACKNOWLEDGEMENT"}
        )
        self.assertEqual(up_resp.status_code, 201)
        self.assertEqual(up_resp.json()["data"]["extraction_status"], "COMPLETED")

        # 4. Trigger workflow engine delay check
        with SessionLocal() as db:
            g_obj = db.get(Grievance, uuid.UUID(gid))
            evaluate_grievance(db, g_obj)

        # 5. Verify notification generated
        notifs = self.client.get("/api/v1/notifications", headers=auth).json()["data"]
        self.assertTrue(len(notifs) > 0)
        self.assertEqual(notifs[0]["notification_type"], "POTENTIAL_DELAY")

        # 6. Fetch plain-language AI explanation
        exp = self.client.get(f"/api/v1/grievances/{gid}/explanation", headers=auth).json()["data"]
        self.assertIn(self.demo_complaint_id, exp["current_situation"])
        self.assertFalse(exp["is_placeholder"])

        # 7. Fetch next-action guidance
        action = self.client.get(f"/api/v1/grievances/{gid}/next-action", headers=auth).json()["data"]
        self.assertEqual(action["type"], "FOLLOW_UP")
        self.assertIsInstance(action["official_source"], str)
        self.assertIn("scores.sebi.gov.in", action["official_source"])


if __name__ == "__main__":
    print("=" * 70)
    print("FLOWGUARD: Person 4 Real API Integration Test Suite (Step 6)")
    print(f"Shared Demo Case: {DEMO_COMPLAINT_ID}")
    print("=" * 70)
    unittest.main(verbosity=2)
