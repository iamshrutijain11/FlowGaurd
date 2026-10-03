"""
summarizer.py - Plain-Language Grievance Summarizer for FlowGuard.

Builds a controlled context object, calls Gemini via the google-genai SDK,
and returns a structured JSON summary (current_situation, what_happened,
possible_missing_information, warning_explanation, next_step_summary).
Includes strict anti-hallucination protections and a deterministic fallback template.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google import genai
from google.genai import types

from app.ai.prompts import SUMMARIZER_SYSTEM_INSTRUCTION, build_summarizer_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables (.env in backend directory or parent)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


# Pydantic models for structured validation
class ControlledContext(BaseModel):
    """Controlled context model ensuring strictly grounded data is passed to AI."""
    grievance: Dict[str, Any] = Field(
        ...,
        description="Core grievance record: complaint_id, entity_name, entity_type, issue, submission_date, current_stage, status"
    )
    events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological event history: timestamp, stage, description, source"
    )
    workflow_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow detection outcome: is_delayed, warning_type, warning_message, days_elapsed"
    )
    documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Uploaded document metadata: document_type, file_name, status, upload_date"
    )
    verified_guidance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Official verified process information: escalation_path, official_portal, conditions, required_docs"
    )


class GrievanceSummaryResponse(BaseModel):
    """Standardized 5-key response contract for the investor summary."""
    current_situation: str = Field(
        ..., description="Plain-language explanation of where the complaint currently stands."
    )
    what_happened: str = Field(
        ..., description="Fact-based chronological summary of recorded events."
    )
    possible_missing_information: str = Field(
        ..., description="Details or documents not yet recorded, or 'None identified based on available records'."
    )
    warning_explanation: str = Field(
        ..., description="Neutral explanation of detected delay or 'No warnings active'."
    )
    next_step_summary: str = Field(
        ..., description="Summary of verified next actions available to the investor."
    )


def build_controlled_context(
    grievance: Dict[str, Any],
    events: Optional[List[Dict[str, Any]]] = None,
    workflow_result: Optional[Dict[str, Any]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    verified_guidance: Optional[Dict[str, Any]] = None,
) -> ControlledContext:
    """
    Constructs and validates the controlled context object for FlowGuard AI.
    Ensures missing collections default safely to empty structures.
    """
    return ControlledContext(
        grievance=grievance,
        events=events or [],
        workflow_result=workflow_result or {},
        documents=documents or [],
        verified_guidance=verified_guidance or {},
    )


def get_fallback_summary(context: Dict[str, Any]) -> Dict[str, str]:
    """
    Deterministic fallback summary generator used if Gemini API call fails,
    times out, or experiences temporary unavailability.
    Maintains the exact same 5-key schema and strict anti-hallucination rules.
    """
    grievance = context.get("grievance", {})
    events = context.get("events", [])
    workflow_result = context.get("workflow_result", {})
    documents = context.get("documents", [])
    verified_guidance = context.get("verified_guidance", {})

    complaint_id = grievance.get("complaint_id", "Not Available")
    entity_name = grievance.get("entity_name", "the intermediary")
    current_stage = grievance.get("current_stage", "Filed")
    submission_date = grievance.get("submission_date", "not available")
    issue = grievance.get("issue_type") or grievance.get("issue", "Transaction related grievance")

    # 1. Current Situation
    current_situation = (
        f"Your complaint ({complaint_id}) against {entity_name} regarding '{issue}' "
        f"is currently in the '{current_stage}' stage."
    )

    # 2. What Happened
    if events:
        event_descriptions = [
            f"On {e.get('timestamp', 'recorded date')}: {e.get('description', e.get('stage', 'Event logged'))}"
            for e in events
        ]
        what_happened = "Recorded timeline: " + "; ".join(event_descriptions) + "."
    else:
        what_happened = f"Complaint was submitted on {submission_date}. No subsequent events are recorded yet."

    # 3. Possible Missing Information
    missing_items = []
    if not documents:
        missing_items.append("supporting documents/acknowledgement receipt")
    if grievance.get("expected_response_date") is None and not workflow_result.get("expected_response_date"):
        missing_items.append("formal response deadline confirmation from intermediary")

    if missing_items:
        possible_missing_information = (
            f"The case record currently does not include: {', '.join(missing_items)}."
        )
    else:
        possible_missing_information = "None identified based on available records."

    # 4. Warning Explanation
    if workflow_result.get("is_delayed"):
        days = workflow_result.get("days_elapsed", "not specified")
        warning_msg = workflow_result.get(
            "warning_message",
            f"The recorded response window appears exceeded ({days} days elapsed) without a recorded response."
        )
        warning_explanation = (
            f"Internal Workflow Notice: {warning_msg} Note: This indicates a potential workflow delay "
            f"tracked by FlowGuard, not a confirmed regulatory finding."
        )
    else:
        warning_explanation = "No warnings active. The grievance is progressing normally within recorded expectations."

    # 5. Next Step Summary
    escalation_path = verified_guidance.get("escalation_path")
    portal = verified_guidance.get("official_portal")
    next_action = verified_guidance.get("recommended_action")

    if escalation_path and portal:
        next_step_summary = (
            f"Recommended official next step: {next_action or 'Follow-up or escalate'}. "
            f"Escalation route: {escalation_path} via the official portal ({portal}). "
            f"Ensure all recorded reference numbers and acknowledgements are kept ready."
        )
    elif escalation_path:
        next_step_summary = f"Recommended next step: {escalation_path}."
    else:
        next_step_summary = (
            f"Awaiting response from {entity_name}. Check back for status updates or upload new responses if received."
        )

    return {
        "current_situation": current_situation,
        "what_happened": what_happened,
        "possible_missing_information": possible_missing_information,
        "warning_explanation": warning_explanation,
        "next_step_summary": next_step_summary,
    }


def clean_json_response(raw_text: str) -> str:
    """Removes potential markdown formatting or code blocks from LLM output."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def summarize_grievance(
    context: Dict[str, Any] | ControlledContext,
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Summarizes a grievance using Gemini via the google-genai SDK.
    
    Args:
        context: ControlledContext model or dictionary containing grievance, events,
                 workflow_result, documents, and verified_guidance.
        model_name: Optional Gemini model name. Defaults to LLM_MODEL in .env or 'gemini-3.8-flash'.
        
    Returns:
        Dict conforming to GrievanceSummaryResponse schema.
    """
    # Convert to standard dict representation
    if isinstance(context, ControlledContext):
        context_dict = context.model_dump()
    else:
        context_dict = context

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        logger.warning("LLM_API_KEY not found in environment. Using fallback summary template.")
        return get_fallback_summary(context_dict)

    chosen_model = model_name or os.getenv("LLM_MODEL", "gemini-3.8-flash")
    prompt = build_summarizer_prompt(context_dict)

    try:
        client = genai.Client(api_key=api_key)
        
        # Configure model call with system instruction and JSON output request
        config = types.GenerateContentConfig(
            system_instruction=SUMMARIZER_SYSTEM_INSTRUCTION,
            temperature=0.2,  # Low temperature for strict factual adherence
            response_mime_type="application/json",
        )

        response = client.models.generate_content(
            model=chosen_model,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or ""
        cleaned_text = clean_json_response(raw_text)
        parsed_json = json.loads(cleaned_text)

        # Validate against Pydantic schema to ensure all 5 keys are present
        validated_response = GrievanceSummaryResponse(**parsed_json)
        return validated_response.model_dump()

    except Exception as e:
        logger.error(f"Gemini API summarization call failed ({type(e).__name__}: {e}). Applying fallback template.")
        # Attempt fallback to gemini-flash-latest if primary model encountered an error
        if chosen_model != "gemini-flash-latest":
            try:
                logger.info("Attempting retry with secondary model 'gemini-flash-latest'...")
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SUMMARIZER_SYSTEM_INSTRUCTION,
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )
                cleaned_text = clean_json_response(response.text or "")
                parsed_json = json.loads(cleaned_text)
                validated_response = GrievanceSummaryResponse(**parsed_json)
                return validated_response.model_dump()
            except Exception as retry_err:
                logger.warning(f"Secondary model retry failed as well: {retry_err}. Using deterministic fallback.")

        return get_fallback_summary(context_dict)


# ============================================================================
# DEMO CASE & INTEGRATION POINTS
# ============================================================================

def get_demo_case_context() -> Dict[str, Any]:
    """
    Standard shared demo case: CMP-2026-DEMO-001 (Track B investor scenario).
    Used for standalone testing until Person 2 and Person 3 backend modules connect.
    """
    # TODO (Person 2 Integration): Replace with call to backend DB / API: GET /api/v1/grievances/CMP-2026-DEMO-001
    grievance = {
        "complaint_id": "CMP-2026-DEMO-001",
        "entity_name": "Demo Brokerage Pvt Ltd",
        "issue_type": "Transaction related grievance",
        "submission_date": "2026-09-20T10:00:00Z",
        "current_stage": "AWAITING_RESPONSE",
        "status": "In Progress",
    }

    # TODO (Person 2 Integration): Replace with call to backend DB / API: GET /api/v1/grievances/CMP-2026-DEMO-001/events
    events = [
        {
            "timestamp": "2026-09-20T10:00:00Z",
            "stage": "FILED",
            "description": "20 Sep: Complaint Filed by investor with Demo Brokerage Pvt Ltd",
            "source": "Investor Portal",
        },
        {
            "timestamp": "2026-09-20T14:30:00Z",
            "stage": "ACKNOWLEDGED",
            "description": "20 Sep: Acknowledgement Received from Demo Brokerage Pvt Ltd",
            "source": "Intermediary Email",
        },
        {
            "timestamp": "2026-09-21T09:00:00Z",
            "stage": "AWAITING_RESPONSE",
            "description": "21 Sep: Awaiting Response from Demo Brokerage Pvt Ltd",
            "source": "System Transition",
        }
    ]

    # TODO (Person 3 Integration): Replace with call to Person 3 Delay Detection Engine / API: GET /api/v1/grievances/CMP-2026-DEMO-001/workflow-status
    workflow_result = {
        "is_delayed": True,
        "warning_type": "response_window_exceeded",
        "warning_message": "Recorded response window appears exceeded (30-day demo configuration window elapsed since filing). No intermediary response recorded. Note: This 30-day window is a demo configuration for simulation purposes, not an official regulatory deadline.",
        "days_elapsed": 30,
        "expected_window_days": 30,
        "window_basis": "demo configuration",
        "current_stage": "AWAITING_RESPONSE"
    }

    # TODO (Person 2 Integration): Replace with call to backend DB / API: GET /api/v1/grievances/CMP-2026-DEMO-001/documents
    documents = [
        {
            "document_id": "DOC-001",
            "document_type": "complaint_acknowledgement",
            "file_name": "acknowledgement_CMP-2026-DEMO-001.pdf",
            "status": "uploaded",
            "upload_date": "2026-09-20T14:30:00Z"
        }
    ]

    # Dynamically fetched from guidance_data/ catalogs via guidance_loader
    from app.ai.guidance_loader import get_guidance
    verified_guidance = get_guidance(
        entity_type=grievance["entity_name"],
        stage=grievance["current_stage"],
        warning_type=workflow_result.get("warning_type"),
    )

    return build_controlled_context(
        grievance=grievance,
        events=events,
        workflow_result=workflow_result,
        documents=documents,
        verified_guidance=verified_guidance,
    ).model_dump()


if __name__ == "__main__":
    print("=" * 70)
    print("FLOWGUARD AI: Plain-Language Grievance Summarizer Test (Step 1)")
    print("=" * 70)

    # 1. Build controlled context from demo case CMP-2026-DEMO-001
    demo_context = get_demo_case_context()
    print("\n[1] Controlled Context Built Successfully:")
    print(f" - Complaint ID: {demo_context['grievance']['complaint_id']}")
    print(f" - Current Stage: {demo_context['grievance']['current_stage']}")
    print(f" - Warning Type: {demo_context['workflow_result']['warning_type']}")

    # 2. Test Gemini API Call
    print("\n[2] Calling Gemini via google-genai SDK...")
    summary = summarize_grievance(demo_context)

    print("\n[3] Resulting AI Summary (JSON):")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # 3. Test Fallback Mechanism
    print("\n[4] Testing Deterministic Fallback Mode (API offline simulation)...")
    fallback = get_fallback_summary(demo_context)
    print(json.dumps(fallback, indent=2, ensure_ascii=False))
    print("\n" + "=" * 70)
    print("Step 1 validation completed successfully!")
    print("=" * 70)
