"""
test_integration_demo.py - Integration Test Suite for FlowGuard (Person 4).

Tests the full Person 4 pipeline using the shared demo case CMP-2026-DEMO-001:
1. Document Extraction (AI extraction with value/confidence objects & fallback).
2. Evidence & Timeline Helper (timeline ordering, suggested documents, completeness).
3. Verified Guidance Loader (official SEBI SCORES / SMART ODR routes, demo disclaimers).
4. Grievance Summarizer (controlled context assembly, 5-key JSON schema, anti-hallucination).
5. Notification Service (in-app, simulated email, simulated SMS, dispatch).
6. End-to-End Pipeline (connects extraction -> evidence -> guidance -> summary -> notifications).
"""

import unittest
import json
from typing import Dict, Any

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
    format_email_demo,
    format_sms_demo,
    get_demo_notifications,
)


class TestFlowGuardPerson4Integration(unittest.TestCase):
    """Full integration test suite for Person 4 deliverables."""

    @classmethod
    def setUpClass(cls):
        cls.demo_complaint_id = "CMP-2026-DEMO-001"
        cls.demo_entity_name = "Demo Brokerage Pvt Ltd"
        cls.demo_stage = "AWAITING_RESPONSE"
        cls.demo_warning = "response_window_exceeded"

    # ------------------------------------------------------------------------
    # 1. Document Extraction Tests
    # ------------------------------------------------------------------------
    def test_01_document_extraction_schema_and_fallback(self):
        """Verify extraction returns {value, confidence} objects marked as suggestions."""
        # Test deterministic fallback first (always available, no external API dependency)
        data = fallback_heuristic_extraction(DEMO_DOCUMENT_TEXT)
        self.assertIsInstance(data, dict)

        # 1. Verify required field structure
        for field in ["complaint_id", "entity_name", "submission_date", "issue_description", "detected_stage"]:
            self.assertIn(field, data)
            self.assertIn("value", data[field])
            self.assertIn("confidence", data[field])
            self.assertIsInstance(data[field]["confidence"], (int, float))
            self.assertGreaterEqual(data[field]["confidence"], 0.0)
            self.assertLessEqual(data[field]["confidence"], 1.0)

        # 2. Verify extracted values match demo case
        self.assertEqual(data["complaint_id"]["value"], self.demo_complaint_id)
        self.assertEqual(data["entity_name"]["value"], self.demo_entity_name)
        self.assertEqual(data["submission_date"]["value"], "2026-09-20")
        self.assertEqual(data["detected_stage"]["value"], "ACKNOWLEDGED")

        # 3. Verify user confirmation suggestion flags
        self.assertTrue(data.get("requires_user_confirmation"))
        self.assertEqual(data.get("status"), "SUGGESTION_PENDING_CONFIRMATION")

        # 4. Validate Pydantic schema deserialization
        validated = ExtractedGrievanceData(**data)
        self.assertEqual(validated.complaint_id.value, self.demo_complaint_id)

    # ------------------------------------------------------------------------
    # 2. Evidence & Timeline Helper Tests
    # ------------------------------------------------------------------------
    def test_02_evidence_helper_stages_and_suggestions(self):
        """Verify evidence helper uses exact 6 stages and 'suggested' non-mandatory wording."""
        # 1. Verify exact 6 canonical stages
        expected_stages = [
            "FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE",
            "RESPONSE_RECEIVED", "RESOLVED", "FURTHER_ACTION"
        ]
        self.assertEqual(sorted(list(STAGE_DOCUMENT_SUGGESTIONS.keys())), sorted(expected_stages))

        # 2. Test demo case evidence report
        report = get_demo_evidence_report()
        self.assertEqual(report["complaint_id"], self.demo_complaint_id)
        self.assertEqual(report["current_stage"], self.demo_stage)

        # 3. Timeline verification
        self.assertEqual(len(report["timeline"]), 3)
        self.assertEqual(report["timeline"][0]["stage"], "FILED")
        self.assertEqual(report["timeline"][1]["stage"], "ACKNOWLEDGED")
        self.assertEqual(report["timeline"][2]["stage"], "AWAITING_RESPONSE")

        # 4. Checklist verification: total_suggested, uploaded, missing
        self.assertEqual(report["total_suggested"], 3)
        self.assertEqual(report["total_uploaded"], 1)
        self.assertEqual(report["total_missing"], 2)
        self.assertEqual(report["completeness_pct"], 33.3)

        # 5. Verify non-mandatory wording ("may be useful for your grievance record")
        for item in report["checklist"]:
            self.assertIn("may be useful for your grievance record", item["guidance_note"].lower())
            self.assertNotIn("legally required", item["guidance_note"].lower())
            self.assertIn(item["status"], ["uploaded", "not_yet_uploaded"])

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

        # Verify demo configuration disclaimer
        self.assertIn("demo configuration", guidance["disclaimer"].lower())
        self.assertIn("warning_guidance", guidance)
        self.assertEqual(guidance["warning_guidance"]["title"], "Response Window Exceeded Notice")

        # Verify escalation matrix (4 tiers)
        matrix = get_escalation_matrix()
        self.assertEqual(len(matrix.get("tiers", [])), 4)
        self.assertEqual(matrix["tiers"][0]["level_name"], "Intermediary Level")
        self.assertEqual(matrix["tiers"][2]["level_name"], "Regulatory Level - SEBI SCORES 2.0")
        self.assertEqual(matrix["tiers"][3]["level_name"], "Online Dispute Resolution (ODR) - SMART ODR Portal")

    # ------------------------------------------------------------------------
    # 4. Grievance Summarizer Tests
    # ------------------------------------------------------------------------
    def test_04_summarizer_controlled_context_and_schema(self):
        """Verify controlled context and 5-key summary schema adherence."""
        context = get_demo_case_context()

        # 1. Controlled context keys
        self.assertIn("grievance", context)
        self.assertIn("events", context)
        self.assertIn("workflow_result", context)
        self.assertIn("documents", context)
        self.assertIn("verified_guidance", context)

        # 2. Test fallback template (deterministic, adheres to 5 keys)
        fallback = get_fallback_summary(context)
        required_keys = [
            "current_situation",
            "what_happened",
            "possible_missing_information",
            "warning_explanation",
            "next_step_summary"
        ]
        for key in required_keys:
            self.assertIn(key, fallback)
            self.assertIsInstance(fallback[key], str)
            self.assertGreater(len(fallback[key]), 10)

        # 3. Check anti-hallucination and neutrality rules
        self.assertIn(self.demo_complaint_id, fallback["current_situation"])
        self.assertIn(self.demo_entity_name, fallback["current_situation"])
        self.assertIn("demo configuration", fallback["warning_explanation"].lower())
        self.assertIn("https://scores.sebi.gov.in", fallback["next_step_summary"])

        # 4. Pydantic schema validation
        validated = GrievanceSummaryResponse(**fallback)
        self.assertIsNotNone(validated.current_situation)

    # ------------------------------------------------------------------------
    # 5. Notification Service Tests
    # ------------------------------------------------------------------------
    def test_05_notifications_generation_and_channels(self):
        """Verify in-app, email, and SMS notification generation and dispatch."""
        notifications_data = get_demo_notifications()
        self.assertEqual(notifications_data["complaint_id"], self.demo_complaint_id)
        self.assertEqual(notifications_data["total_notifications"], 5)

        # Verify in-app notifications
        in_app = notifications_data["in_app_notifications"]
        types = [n["type"] for n in in_app]
        self.assertIn("STAGE_TRANSITION", types)
        self.assertIn("DELAY_WARNING", types)
        self.assertIn("EVIDENCE_REMINDER", types)
        self.assertIn("NEXT_ACTION_GUIDANCE", types)

        # Check warning notification contents
        warn_notif = next(n for n in in_app if n["type"] == "DELAY_WARNING")
        self.assertEqual(warn_notif["severity"], "WARNING")
        self.assertIn("demo configuration", warn_notif["message"].lower())

        # Check simulated email format
        email = notifications_data["simulated_email"]
        self.assertEqual(email["channel"], "EMAIL_DEMO")
        self.assertIn("investor.ramesh@example.com", email["recipient"])
        self.assertIn(self.demo_complaint_id, email["body"])

        # Check simulated SMS format
        sms = notifications_data["simulated_sms"]
        self.assertEqual(sms["channel"], "SMS_DEMO")
        self.assertIn(self.demo_complaint_id, sms["sms_text"])

        # Test dispatch service
        service = NotificationService()
        test_item = NotificationItem(**in_app[0])
        res = service.dispatch(test_item)
        self.assertEqual(res["status"], "DISPATCHED")
        stored = service.get_notifications_for_complaint(self.demo_complaint_id)
        self.assertEqual(len(stored), 1)

    # ------------------------------------------------------------------------
    # 6. End-to-End Pipeline Integration Test
    # ------------------------------------------------------------------------
    def test_06_end_to_end_person4_pipeline(self):
        """
        Tests the complete Person 4 workflow:
        Document Ingestion -> Evidence Helper -> Verified Guidance -> Summary -> Notification Dispatch.
        """
        # Step A: Ingestion from document text
        extracted = fallback_heuristic_extraction(DEMO_DOCUMENT_TEXT)
        complaint_id = extracted["complaint_id"]["value"]
        entity_name = extracted["entity_name"]["value"]
        submission_date = extracted["submission_date"]["value"]
        self.assertEqual(complaint_id, self.demo_complaint_id)

        # Step B: Grievance & Events setup (mocked backend contract)
        grievance = {
            "complaint_id": complaint_id,
            "entity_name": entity_name,
            "issue_type": "Transaction related grievance",
            "submission_date": submission_date,
            "current_stage": "AWAITING_RESPONSE",
            "status": "In Progress",
        }
        events = [
            {"timestamp": f"{submission_date}T10:00:00Z", "stage": "FILED", "description": "20 Sep: Complaint Filed", "source": "Investor Portal"},
            {"timestamp": f"{submission_date}T14:30:00Z", "stage": "ACKNOWLEDGED", "description": "20 Sep: Acknowledgement Received", "source": "Intermediary Email"},
            {"timestamp": "2026-09-21T09:00:00Z", "stage": "AWAITING_RESPONSE", "description": "21 Sep: Awaiting Response", "source": "System Transition"},
        ]
        documents = [
            {"document_id": "DOC-001", "document_type": "complaint_acknowledgement", "file_name": f"acknowledgement_{complaint_id}.pdf", "status": "uploaded"}
        ]

        # Step C: Evidence Checklist & Timeline calculation
        evidence_report = build_evidence_report(grievance, events, documents)
        self.assertEqual(evidence_report["total_uploaded"], 1)
        self.assertEqual(evidence_report["total_missing"], 2)

        # Step D: Verified Guidance dynamic lookup
        workflow_result = {
            "is_delayed": True,
            "warning_type": "response_window_exceeded",
            "warning_message": "Recorded response window appears exceeded (30-day demo configuration window elapsed).",
            "days_elapsed": 30,
            "expected_window_days": 30,
            "window_basis": "demo configuration",
            "current_stage": "AWAITING_RESPONSE",
        }
        guidance = get_guidance(entity_name, grievance["current_stage"], workflow_result["warning_type"])
        self.assertEqual(guidance["escalation_path"], "SEBI SCORES 2.0 / SMART ODR Portal")

        # Step E: Controlled Context & AI Summary
        controlled_ctx = build_controlled_context(
            grievance=grievance,
            events=events,
            workflow_result=workflow_result,
            documents=documents,
            verified_guidance=guidance,
        ).model_dump()
        summary = get_fallback_summary(controlled_ctx)
        self.assertIn("AWAITING_RESPONSE", summary["current_situation"])
        self.assertIn("scores.sebi.gov.in", summary["next_step_summary"])

        # Step F: Notification Generation
        notif = create_delay_warning_notification(
            complaint_id=complaint_id,
            entity_name=entity_name,
            stage=grievance["current_stage"],
            warning_type=workflow_result["warning_type"],
            days_elapsed=30,
        )
        self.assertEqual(notif.severity, "WARNING")
        self.assertIn("demo configuration", notif.message.lower())


if __name__ == "__main__":
    print("=" * 70)
    print("FLOWGUARD: Person 4 Integration Test Suite (Step 6)")
    print("Shared Demo Case: CMP-2026-DEMO-001")
    print("=" * 70)
    unittest.main(verbosity=2)
