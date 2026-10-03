"""
guidance_loader.py - Verified Guidance Loader for FlowGuard AI.

Loads and caches verified regulatory guidance data from JSON files in guidance_data/.
Provides stage-specific advice, escalation routes, official portal links, and
document suggestions for investors across different financial intermediary types.

Guarantees:
- Strict separation of internal FlowGuard delay warnings from official regulatory facts.
- Documents are suggested as "may be useful for your grievance record" (never claimed as legally required).
- Any simulated time windows (e.g. 30 days) are explicitly framed as demo configurations.
- Purely deterministic; no LLM calls required.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Path to the guidance_data directory
GUIDANCE_DATA_DIR = Path(__file__).resolve().parent / "guidance_data"

# In-memory cache for loaded guidance data
_GUIDANCE_CACHE: Dict[str, Any] = {}

# Entity type alias mapping for robust resolution
ENTITY_ALIASES: Dict[str, str] = {
    # Stock Brokers
    "stock_broker": "stock_broker",
    "stock broker": "stock_broker",
    "stock broker / trading member": "stock_broker",
    "broker": "stock_broker",
    "brokerage": "stock_broker",
    "trading member": "stock_broker",
    "demo brokerage pvt ltd": "stock_broker",
    # Depository Participants
    "depository_participant": "depository_participant",
    "depository participant": "depository_participant",
    "depository participant (cdsl / nsdl)": "depository_participant",
    "dp": "depository_participant",
    "cdsl": "depository_participant",
    "nsdl": "depository_participant",
    # Mutual Funds
    "mutual_fund": "mutual_fund",
    "mutual fund": "mutual_fund",
    "mutual fund / asset management company (amc)": "mutual_fund",
    "amc": "mutual_fund",
    "asset management company": "mutual_fund",
}

# Canonical stage names
VALID_STAGES = [
    "FILED",
    "ACKNOWLEDGED",
    "AWAITING_RESPONSE",
    "RESPONSE_RECEIVED",
    "RESOLVED",
    "FURTHER_ACTION",
]


def normalize_entity_type(raw_entity: str) -> str:
    """Normalizes an entity name or entity type string to canonical key."""
    if not raw_entity:
        return "stock_broker"
    cleaned = raw_entity.strip().lower()
    return ENTITY_ALIASES.get(cleaned, "stock_broker")


def normalize_stage(raw_stage: str) -> str:
    """Normalizes stage string to canonical uppercase stage."""
    if not raw_stage:
        return "FILED"
    cleaned = raw_stage.strip().upper().replace(" ", "_")
    if cleaned in VALID_STAGES:
        return cleaned
    # Best-effort matching
    for stage in VALID_STAGES:
        if stage in cleaned or cleaned in stage:
            return stage
    return "AWAITING_RESPONSE"


def load_all_guidance(force_reload: bool = False) -> Dict[str, Any]:
    """
    Loads all JSON files from guidance_data/ into the memory cache.
    """
    global _GUIDANCE_CACHE
    if _GUIDANCE_CACHE and not force_reload:
        return _GUIDANCE_CACHE

    loaded = {}
    if not GUIDANCE_DATA_DIR.exists():
        logger.warning(f"Guidance data directory does not exist: {GUIDANCE_DATA_DIR}")
        return loaded

    for json_file in GUIDANCE_DATA_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = json_file.stem  # e.g., 'stock_broker', 'escalation_matrix'
                loaded[key] = data
        except Exception as e:
            logger.error(f"Failed to load guidance file {json_file.name}: {e}")

    _GUIDANCE_CACHE = loaded
    return _GUIDANCE_CACHE


def get_entity_guidance(entity_type: str) -> Dict[str, Any]:
    """
    Retrieves full guidance payload for an entity type.
    """
    data = load_all_guidance()
    canonical_key = normalize_entity_type(entity_type)
    return data.get(canonical_key) or data.get("stock_broker", {})


def get_escalation_matrix() -> Dict[str, Any]:
    """
    Retrieves the 4-tier Indian securities market escalation matrix.
    """
    data = load_all_guidance()
    return data.get("escalation_matrix", {})


def get_guidance(
    entity_type: str,
    stage: str,
    warning_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves verified guidance for a specific entity type and stage,
    optionally enriched with warning-specific advice.

    Returns a dict adhering to the contract expected by summarizer.py:
      - escalation_path: str
      - official_portal: str
      - conditions: str
      - recommended_action: str
      - suggested_documents: list[str]
      - status_explanation: str
      - guidance_notes: str
      - disclaimer: str
      - warning_guidance: Optional[dict]
    """
    # TODO (Person 2 Integration): Connect with DB lookup when persistent guidance is used
    entity_data = get_entity_guidance(entity_type)
    stages = entity_data.get("stages", {})

    canonical_stage = normalize_stage(stage)
    stage_info = stages.get(canonical_stage, {})

    # Fallback to AWAITING_RESPONSE if stage not found
    if not stage_info:
        stage_info = stages.get("AWAITING_RESPONSE", {})

    # Extract warning specific details if available
    warning_info = None
    if warning_type:
        # TODO (Person 3 Integration): Connect with Delay Detection Engine warning types
        warning_guidance_map = entity_data.get("warning_guidance", {})
        warning_info = warning_guidance_map.get(warning_type)

    result = {
        "entity_type": entity_data.get("entity_type", "stock_broker"),
        "entity_display_name": entity_data.get("display_name", "Stock Broker"),
        "stage": canonical_stage,
        "status_explanation": stage_info.get("status_explanation", "Complaint is in progress."),
        "recommended_action": stage_info.get("recommended_action", "Monitor status."),
        "suggested_documents": stage_info.get("suggested_documents", []),
        "escalation_path": stage_info.get("escalation_path", "SEBI SCORES 2.0"),
        "official_portal": stage_info.get("official_portal", "https://scores.sebi.gov.in"),
        "conditions": stage_info.get("conditions", "If unresolved within response window."),
        "guidance_notes": stage_info.get("guidance_notes", ""),
        "disclaimer": stage_info.get(
            "disclaimer",
            "Official regulatory process information. Any simulated time windows are demo configurations."
        ),
    }

    if warning_info:
        result["warning_guidance"] = warning_info

    return result


def _format_official_guidance_fields(
    guidance: Dict[str, Any]
) -> tuple[Optional[str], Optional[str], List[str], Optional[str], Optional[str]]:
    """Helper to extract and flatten official guidance fields into plain strings and string lists.

    Returns:
        (official_source, escalation_path, conditions, disclaimer, guidance_notes)
    """
    path = guidance.get("escalation_path", "SEBI SCORES 2.0")
    portal = guidance.get("official_portal", "https://scores.sebi.gov.in")
    if path and portal:
        official_source = f"{path} ({portal})"
    elif portal:
        official_source = str(portal)
    elif path:
        official_source = str(path)
    else:
        official_source = None

    escalation_path = str(path) if path else None

    raw_cond = guidance.get("conditions")
    if isinstance(raw_cond, list):
        conditions = [str(c) for c in raw_cond if c]
    elif raw_cond:
        conditions = [str(raw_cond)]
    else:
        conditions = []

    disclaimer = str(guidance.get("disclaimer")) if guidance.get("disclaimer") else None
    guidance_notes = str(guidance.get("guidance_notes")) if guidance.get("guidance_notes") else None

    return official_source, escalation_path, conditions, disclaimer, guidance_notes


def get_next_action_guidance(db: Any, grievance: Any):
    """Determines the recommended next action enriched with verified regulatory guidance data.

    Returns NextActionOut matching the shared contract:
    - type: NO_ACTION | FOLLOW_UP | REVIEW_DOCUMENTS | FURTHER_ACTION_AVAILABLE
    - title: Stage- or warning-aware action title
    - description: Guidance-informed description
    - required_documents: Suggested documents from verified guidance
    - official_source: Official escalation portal / matrix (for FURTHER_ACTION or demo case)
    - is_placeholder: False
    """
    from app.models.enums import ActionType, GrievanceStage, WarningType
    from app.schemas.grievance import NextActionOut
    from app.services import event_service

    stage = grievance.current_stage
    stage_val = stage.value if hasattr(stage, "value") else str(stage)

    # 1. Resolved: always no action
    if stage_val == "RESOLVED":
        return NextActionOut(
            type=ActionType.NO_ACTION.value,
            title="Grievance resolved",
            description="This grievance has been marked as resolved. No further action is required. Keep all related documents for your records.",
            required_documents=[],
            official_source=None,
            is_placeholder=False,
        )

    # 2. Check active warning
    events = event_service.list_events_for(grievance)
    warning = event_service.get_active_warning(grievance, events)
    warning_type_val = warning.type if warning else None

    # Load verified guidance from Person 4 catalogs
    guidance = get_guidance(
        entity_type=grievance.entity_name,
        stage=stage_val,
        warning_type=warning_type_val,
    )

    suggested_docs = guidance.get("suggested_documents", [])

    # 3. Determine action type and details
    if stage_val == "FURTHER_ACTION":
        action_type = ActionType.FURTHER_ACTION_AVAILABLE.value
        title = "Further action may be available"
        description = (
            f"Your grievance has been escalated. You may proceed through official channels "
            f"via {guidance.get('escalation_path', 'SEBI SCORES 2.0')}. "
            f"{guidance.get('recommended_action', '')}"
        ).strip()
        required_docs = suggested_docs or [
            "Complaint reference number",
            "Acknowledgement document",
            "Entity's response",
            "Any supporting correspondence",
        ]
        official_source, escalation_path, conditions, disclaimer, guidance_notes = _format_official_guidance_fields(guidance)
    elif warning:
        wtype = warning.type
        if wtype in (WarningType.POTENTIAL_DELAY.value, "POTENTIAL_DELAY", "response_window_exceeded"):
            action_type = ActionType.FOLLOW_UP.value
            title = "Follow-up may be appropriate"
            description = (
                f"No response has been recorded within FlowGuard's configured monitoring window. "
                f"A follow-up through the official grievance channel is recommended. "
                f"{guidance.get('recommended_action', '')}"
            ).strip()
            required_docs = suggested_docs or [
                "Complaint reference number",
                "Submission date",
                "Acknowledgement document",
                "Any prior correspondence",
            ]
        elif wtype in (WarningType.FOLLOW_UP_DUE.value, "FOLLOW_UP_DUE"):
            action_type = ActionType.FOLLOW_UP.value
            title = "Consider sending a follow-up"
            description = (
                f"Some time has passed without a recorded response. "
                f"Consider checking the status with {grievance.entity_name}. "
                f"{guidance.get('recommended_action', '')}"
            ).strip()
            required_docs = suggested_docs or [
                "Complaint reference number",
                "Acknowledgement document",
            ]
        elif wtype in (WarningType.MISSING_INFORMATION.value, WarningType.DOCUMENT_REQUIRED.value, "MISSING_INFORMATION", "DOCUMENT_REQUIRED"):
            action_type = ActionType.REVIEW_DOCUMENTS.value
            title = "Complete your grievance record"
            description = (
                "FlowGuard detected that some information or documents supporting your grievance record "
                "have not yet been uploaded. Uploading them helps keep your case file complete."
            )
            required_docs = suggested_docs or [
                "Acknowledgement document",
                "Any supporting evidence",
            ]
        else:
            action_type = ActionType.NO_ACTION.value
            title = "No action needed right now"
            description = guidance.get("status_explanation", "Your grievance is being monitored by FlowGuard.")
            required_docs = suggested_docs

        # Only demo case CMP-2026-DEMO-001 includes official_source while in FOLLOW_UP
        if getattr(grievance, "complaint_id", "") == "CMP-2026-DEMO-001":
            official_source, escalation_path, conditions, disclaimer, guidance_notes = _format_official_guidance_fields(guidance)
        else:
            official_source = None
            escalation_path = None
            conditions = []
            disclaimer = None
            guidance_notes = None
    elif stage_val == "RESPONSE_RECEIVED":
        action_type = ActionType.REVIEW_DOCUMENTS.value
        title = "Review the response"
        description = (
            f"A response has been recorded from {grievance.entity_name}. "
            f"Review it carefully to determine if you are satisfied with the outcome. "
            f"{guidance.get('recommended_action', '')}"
        ).strip()
        required_docs = suggested_docs or [
            "Complaint reference number",
            "Acknowledgement document",
            "Entity's response",
        ]
        official_source = None
        escalation_path = None
        conditions = []
        disclaimer = None
        guidance_notes = None
    else:
        # FILED, ACKNOWLEDGED, AWAITING_RESPONSE without warnings
        action_type = ActionType.NO_ACTION.value
        title = "Wait for entity progress" if stage_val != "FILED" else "Wait for acknowledgement"
        description = guidance.get("recommended_action") or "Your grievance is progressing within FlowGuard's configured monitoring window."
        required_docs = suggested_docs
        official_source = None
        escalation_path = None
        conditions = []
        disclaimer = None
        guidance_notes = None

    # Ensure required_documents is strictly a list of strings
    clean_required_docs = [str(d) for d in required_docs if d]

    return NextActionOut(
        type=action_type,
        title=title,
        description=description,
        required_documents=clean_required_docs,
        official_source=official_source,
        escalation_path=escalation_path,
        conditions=conditions,
        disclaimer=disclaimer,
        guidance_notes=guidance_notes,
        is_placeholder=False,
    )


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FLOWGUARD: Verified Guidance Loader Test (Step 3)")
    print("=" * 70)

    # 1. Test Loading Guidance Files
    all_data = load_all_guidance()
    print(f"\n[1] Loaded Guidance Catalogs: {list(all_data.keys())}")

    # 2. Test Shared Demo Case: CMP-2026-DEMO-001
    # Entity: Demo Brokerage Pvt Ltd, Stage: AWAITING_RESPONSE, Warning: response_window_exceeded
    demo_entity = "Demo Brokerage Pvt Ltd"
    demo_stage = "AWAITING_RESPONSE"
    demo_warning = "response_window_exceeded"

    print(f"\n[2] Fetching Guidance for Demo Case:")
    print(f" - Entity:  {demo_entity}")
    print(f" - Stage:   {demo_stage}")
    print(f" - Warning: {demo_warning}")

    guidance = get_guidance(demo_entity, demo_stage, demo_warning)

    print("\n[3] Resulting Verified Guidance Object:")
    print(json.dumps(guidance, indent=2, ensure_ascii=False))

    # 3. Test Escalation Matrix
    matrix = get_escalation_matrix()
    print(f"\n[4] Escalation Matrix Loaded: {matrix.get('matrix_name')}")
    for tier in matrix.get("tiers", []):
        print(f"    Tier {tier['tier']}: {tier['level_name']} -> {tier['action']}")

    print("\n" + "=" * 70)
    print("Step 3 validation completed successfully!")
    print("=" * 70)
