"""
evidence_helper.py — Document & Evidence Checklist Helper for FlowGuard.

Builds a structured evidence checklist for a grievance case by comparing
uploaded documents against stage-specific suggestions, organising a
complaint timeline from recorded events, and identifying documents that
may be useful for the investor's grievance record.

All logic is deterministic (rule-based).  No AI calls are made here — this
module provides *input* that the AI summarizer can reference, and a
standalone checklist the frontend can render directly.

Document type taxonomy (shared contract with Person 2):
  complaint_acknowledgement  — broker/intermediary acknowledgement receipt
  complaint_copy             — copy of the original complaint filed
  transaction_statement      — account / demat / transaction statement
  intermediary_response      — response letter from the intermediary
  escalation_receipt         — receipt from SEBI SCORES / SMART ODR filing
  supporting_evidence        — any other investor-uploaded evidence
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChecklistItem(BaseModel):
    """One row of the evidence checklist."""
    document_type: str = Field(
        ..., description="Canonical document type key."
    )
    label: str = Field(
        ..., description="Human-readable label for the investor."
    )
    suggested_for_stage: str = Field(
        ..., description="Pipeline stage this document becomes relevant at."
    )
    status: str = Field(
        ..., description="'uploaded' | 'not_yet_uploaded' | 'not_suggested_yet'"
    )
    file_name: Optional[str] = Field(
        default=None, description="File name if uploaded."
    )
    upload_date: Optional[str] = Field(
        default=None, description="ISO timestamp of upload, if available."
    )
    guidance_note: str = Field(
        default="", description="Short helper note for the investor."
    )


class TimelineEntry(BaseModel):
    """One entry in the organised complaint timeline."""
    timestamp: str
    stage: str
    description: str
    source: str
    days_since_filing: Optional[int] = Field(
        default=None,
        description="Calendar days elapsed since original filing date."
    )


class EvidenceReport(BaseModel):
    """Complete evidence-helper output for a single grievance."""
    complaint_id: str
    current_stage: str
    timeline: List[TimelineEntry]
    checklist: List[ChecklistItem]
    total_suggested: int = Field(
        ..., description="Total documents suggested for the current stage."
    )
    total_uploaded: int = Field(
        ..., description="How many of the suggested documents are uploaded."
    )
    total_missing: int = Field(
        ..., description="How many suggested documents are not yet uploaded."
    )
    completeness_pct: float = Field(
        ..., description="Percentage of suggested documents uploaded (0-100)."
    )
    summary_text: str = Field(
        ..., description="Plain-language evidence readiness summary."
    )


# ---------------------------------------------------------------------------
# Stage-specific document suggestions
# ---------------------------------------------------------------------------

# Maps each pipeline stage to the document types that may be useful on file
# *by that stage*.  Ordered from earliest to latest.
# Stages: FILED, ACKNOWLEDGED, AWAITING_RESPONSE, RESPONSE_RECEIVED,
#         RESOLVED, FURTHER_ACTION
STAGE_DOCUMENT_SUGGESTIONS: Dict[str, List[Dict[str, str]]] = {
    "FILED": [
        {
            "document_type": "complaint_copy",
            "label": "Copy of original complaint",
            "guidance_note": (
                "Keeping a copy of the complaint you submitted (screenshot, "
                "PDF, or email) may be useful for your grievance record."
            ),
        },
    ],
    "ACKNOWLEDGED": [
        {
            "document_type": "complaint_copy",
            "label": "Copy of original complaint",
            "guidance_note": (
                "Keeping a copy of the complaint you submitted (screenshot, "
                "PDF, or email) may be useful for your grievance record."
            ),
        },
        {
            "document_type": "complaint_acknowledgement",
            "label": "Acknowledgement receipt from intermediary",
            "guidance_note": (
                "The confirmation email or letter the broker/intermediary "
                "sent after receiving your complaint may be useful for your grievance record."
            ),
        },
    ],
    "AWAITING_RESPONSE": [
        {
            "document_type": "complaint_copy",
            "label": "Copy of original complaint",
            "guidance_note": (
                "Keeping a copy of the complaint you submitted (screenshot, "
                "PDF, or email) may be useful for your grievance record."
            ),
        },
        {
            "document_type": "complaint_acknowledgement",
            "label": "Acknowledgement receipt from intermediary",
            "guidance_note": (
                "The confirmation email or letter the broker/intermediary "
                "sent after receiving your complaint may be useful for your grievance record."
            ),
        },
        {
            "document_type": "transaction_statement",
            "label": "Account / transaction statement",
            "guidance_note": (
                "A bank, demat, or trading statement showing the disputed "
                "transaction may be useful for your grievance record, especially if you escalate."
            ),
        },
    ],
    "RESPONSE_RECEIVED": [
        {
            "document_type": "complaint_copy",
            "label": "Copy of original complaint",
            "guidance_note": "May be useful for comparison with the intermediary's response.",
        },
        {
            "document_type": "complaint_acknowledgement",
            "label": "Acknowledgement receipt from intermediary",
            "guidance_note": "Having proof of receipt on file may be useful for your grievance record.",
        },
        {
            "document_type": "transaction_statement",
            "label": "Account / transaction statement",
            "guidance_note": "Statement showing the disputed transaction may be useful for your grievance record.",
        },
        {
            "document_type": "intermediary_response",
            "label": "Response letter from intermediary",
            "guidance_note": (
                "Uploading the response you received may be useful so FlowGuard can track "
                "resolution or further action."
            ),
        },
    ],
    "RESOLVED": [
        {
            "document_type": "complaint_copy",
            "label": "Copy of original complaint",
            "guidance_note": "May be useful to retain for your personal records.",
        },
        {
            "document_type": "complaint_acknowledgement",
            "label": "Acknowledgement receipt from intermediary",
            "guidance_note": "May be useful to retain for your personal records.",
        },
        {
            "document_type": "intermediary_response",
            "label": "Response / resolution letter from intermediary",
            "guidance_note": "Final resolution document may be useful for your grievance record.",
        },
    ],
    "FURTHER_ACTION": [
        {
            "document_type": "complaint_copy",
            "label": "Copy of original complaint",
            "guidance_note": "May be useful for your grievance record if you pursue further action or escalation.",
        },
        {
            "document_type": "complaint_acknowledgement",
            "label": "Acknowledgement receipt from intermediary",
            "guidance_note": "May be useful for your grievance record if you pursue further action or escalation.",
        },
        {
            "document_type": "transaction_statement",
            "label": "Account / transaction statement",
            "guidance_note": "May be useful for your grievance record when filing with SEBI SCORES / SMART ODR.",
        },
        {
            "document_type": "escalation_receipt",
            "label": "Escalation filing receipt (SCORES / SMART ODR)",
            "guidance_note": (
                "If you file an escalation, uploading the receipt or reference number "
                "may be useful for your grievance record."
            ),
        },
    ],
}

# Fallback if stage is unknown — suggest at least the basics.
_DEFAULT_SUGGESTIONS = STAGE_DOCUMENT_SUGGESTIONS["AWAITING_RESPONSE"]


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Best-effort ISO timestamp parse."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def build_timeline(
    events: List[Dict[str, Any]],
    submission_date: Optional[str] = None,
) -> List[TimelineEntry]:
    """
    Organises raw event dicts into a sorted, enriched timeline.

    Each entry gets a ``days_since_filing`` field calculated from the
    ``submission_date`` (if parseable).
    """
    filing_dt = _parse_timestamp(submission_date) if submission_date else None

    entries: List[TimelineEntry] = []
    for ev in events:
        ts_raw = ev.get("timestamp", "")
        ev_dt = _parse_timestamp(ts_raw)
        days_since: Optional[int] = None
        if filing_dt and ev_dt:
            days_since = max((ev_dt - filing_dt).days, 0)

        entries.append(
            TimelineEntry(
                timestamp=ts_raw,
                stage=ev.get("stage", "UNKNOWN"),
                description=ev.get("description", "Event recorded"),
                source=ev.get("source", "System"),
                days_since_filing=days_since,
            )
        )

    # Sort chronologically (earliest first)
    entries.sort(key=lambda e: e.timestamp)
    return entries


def build_checklist(
    current_stage: str,
    documents: List[Dict[str, Any]],
) -> List[ChecklistItem]:
    """
    Compares uploaded documents against stage-specific suggestions and
    returns a full checklist with status for each item.
    """
    suggestions = STAGE_DOCUMENT_SUGGESTIONS.get(
        current_stage, _DEFAULT_SUGGESTIONS
    )

    # Index uploaded docs by document_type for quick lookup
    uploaded_index: Dict[str, Dict[str, Any]] = {}
    for doc in documents:
        doc_type = doc.get("document_type", "")
        if doc_type:
            uploaded_index[doc_type] = doc

    checklist: List[ChecklistItem] = []
    for sug in suggestions:
        doc_type = sug["document_type"]
        uploaded = uploaded_index.get(doc_type)

        if uploaded:
            checklist.append(
                ChecklistItem(
                    document_type=doc_type,
                    label=sug["label"],
                    suggested_for_stage=current_stage,
                    status="uploaded",
                    file_name=uploaded.get("file_name"),
                    upload_date=uploaded.get("upload_date"),
                    guidance_note=sug.get("guidance_note", ""),
                )
            )
        else:
            checklist.append(
                ChecklistItem(
                    document_type=doc_type,
                    label=sug["label"],
                    suggested_for_stage=current_stage,
                    status="not_yet_uploaded",
                    guidance_note=sug.get("guidance_note", ""),
                )
            )

    # Also list any *extra* uploaded docs not in the suggestions
    suggested_types = {s["document_type"] for s in suggestions}
    for doc in documents:
        doc_type = doc.get("document_type", "")
        if doc_type and doc_type not in suggested_types:
            checklist.append(
                ChecklistItem(
                    document_type=doc_type,
                    label=doc.get("label", doc_type.replace("_", " ").title()),
                    suggested_for_stage="supplementary",
                    status="uploaded",
                    file_name=doc.get("file_name"),
                    upload_date=doc.get("upload_date"),
                    guidance_note="Additional evidence uploaded by investor.",
                )
            )

    return checklist


def _build_summary_text(
    complaint_id: str,
    current_stage: str,
    total_suggested: int,
    total_uploaded: int,
    total_missing: int,
    missing_labels: List[str],
) -> str:
    """Plain-language evidence readiness summary for the investor."""
    if total_missing == 0:
        return (
            f"All {total_suggested} documents suggested for the "
            f"'{current_stage}' stage of complaint {complaint_id} are on file. "
            f"Your evidence checklist is complete."
        )

    missing_list = "; ".join(missing_labels)
    return (
        f"For complaint {complaint_id} at the '{current_stage}' stage, "
        f"{total_uploaded} of {total_suggested} suggested documents are uploaded. "
        f"{total_missing} document(s) not yet uploaded: {missing_list}. "
        f"Having these on file may be useful for your grievance record."
    )


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def build_evidence_report(
    grievance: Dict[str, Any],
    events: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Builds the full evidence report for a grievance.

    Args:
        grievance: Core grievance dict (complaint_id, current_stage,
                   submission_date, etc.)
        events:    Chronological event list from Person 2 DB / demo data.
        documents: Uploaded document metadata list from Person 2 DB / demo data.

    Returns:
        Dict representation of an EvidenceReport.
    """
    complaint_id = grievance.get("complaint_id", "UNKNOWN")
    current_stage = grievance.get("current_stage", "FILED")
    submission_date = grievance.get("submission_date")

    # TODO (Person 2 Integration): Replace with live DB call
    #   GET /api/v1/grievances/{complaint_id}/events
    #   GET /api/v1/grievances/{complaint_id}/documents

    timeline = build_timeline(events, submission_date)
    checklist = build_checklist(current_stage, documents)

    suggested_items = [c for c in checklist if c.suggested_for_stage == current_stage]
    total_suggested = len(suggested_items)
    total_uploaded = sum(1 for c in suggested_items if c.status == "uploaded")
    total_missing = total_suggested - total_uploaded
    completeness_pct = round(
        (total_uploaded / total_suggested * 100) if total_suggested else 100.0, 1
    )

    missing_labels = [c.label for c in suggested_items if c.status == "not_yet_uploaded"]

    summary_text = _build_summary_text(
        complaint_id, current_stage,
        total_suggested, total_uploaded, total_missing,
        missing_labels,
    )

    report = EvidenceReport(
        complaint_id=complaint_id,
        current_stage=current_stage,
        timeline=timeline,
        checklist=checklist,
        total_suggested=total_suggested,
        total_uploaded=total_uploaded,
        total_missing=total_missing,
        completeness_pct=completeness_pct,
        summary_text=summary_text,
    )

    return report.model_dump()


# ---------------------------------------------------------------------------
# Demo case helper (reuses shared CMP-2026-DEMO-001 data)
# ---------------------------------------------------------------------------

def get_demo_evidence_report() -> Dict[str, Any]:
    """
    Builds an evidence report for the shared demo case CMP-2026-DEMO-001.
    Imports demo data from summarizer to guarantee a single source of truth.
    """
    from app.ai.summarizer import get_demo_case_context

    ctx = get_demo_case_context()
    return build_evidence_report(
        grievance=ctx["grievance"],
        events=ctx["events"],
        documents=ctx["documents"],
    )


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=" * 70)
    print("FLOWGUARD: Evidence & Document Checklist Helper Test (Step 2)")
    print("=" * 70)

    report = get_demo_evidence_report()

    print(f"\n[1] Complaint: {report['complaint_id']}")
    print(f"    Stage:     {report['current_stage']}")

    print("\n[2] Organised Timeline:")
    for entry in report["timeline"]:
        print(
            f"    {entry['timestamp']}  |  {entry['stage']:20s}  |  "
            f"{entry['description']}  (day {entry['days_since_filing']})"
        )

    print("\n[3] Evidence Checklist:")
    for item in report["checklist"]:
        icon = "[OK]" if item["status"] == "uploaded" else "[NOT YET UPLOADED]"
        fname = f"  [{item['file_name']}]" if item["file_name"] else ""
        print(f"    {icon} {item['label']}{fname}")
        if item["status"] == "not_yet_uploaded":
            print(f"       -> {item['guidance_note']}")

    print(f"\n[4] Completeness: {report['total_uploaded']}/{report['total_suggested']}"
          f" ({report['completeness_pct']}%)")
    print(f"    Not yet uploaded: {report['total_missing']}")

    print(f"\n[5] Summary: {report['summary_text']}")

    print("\n[6] Full JSON Report:")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("Step 2 validation completed successfully!")
    print("=" * 70)
