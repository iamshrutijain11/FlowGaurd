"""
app.ai - FlowGuard AI & Guidance Package (Person 4).

Modules:
- summarizer: Plain-language status summarizer using Google Gemini SDK & fallback templates.
- prompts: System instructions and strict anti-hallucination templates.
- evidence_helper: Deterministic evidence checklist & timeline builder.
- guidance_loader: Verified official regulatory guidance loader from JSON catalogs.
- extraction: AI document and acknowledgement information extraction.
"""

from app.ai.prompts import (
    SUMMARIZER_SYSTEM_INSTRUCTION,
    build_summarizer_prompt,
)
from app.ai.summarizer import (
    ControlledContext,
    GrievanceSummaryResponse,
    build_controlled_context,
    get_fallback_summary,
    summarize_grievance,
    get_demo_case_context,
)
from app.ai.evidence_helper import (
    ChecklistItem,
    TimelineEntry,
    EvidenceReport,
    STAGE_DOCUMENT_SUGGESTIONS,
    build_timeline,
    build_checklist,
    build_evidence_report,
    get_demo_evidence_report,
)
from app.ai.guidance_loader import (
    get_guidance,
    get_entity_guidance,
    get_escalation_matrix,
    load_all_guidance,
    normalize_entity_type,
    normalize_stage,
)
from app.ai.extraction import (
    ExtractedField,
    ExtractedGrievanceData,
    extract_grievance_data,
    fallback_heuristic_extraction,
    process_document_extraction,
)

__all__ = [
    # Summarizer
    "ControlledContext",
    "GrievanceSummaryResponse",
    "build_controlled_context",
    "get_fallback_summary",
    "summarize_grievance",
    "get_demo_case_context",
    # Prompts
    "SUMMARIZER_SYSTEM_INSTRUCTION",
    "build_summarizer_prompt",
    # Evidence Helper
    "ChecklistItem",
    "TimelineEntry",
    "EvidenceReport",
    "STAGE_DOCUMENT_SUGGESTIONS",
    "build_timeline",
    "build_checklist",
    "build_evidence_report",
    "get_demo_evidence_report",
    # Guidance Loader
    "get_guidance",
    "get_entity_guidance",
    "get_escalation_matrix",
    "load_all_guidance",
    "normalize_entity_type",
    "normalize_stage",
    # Extraction
    "ExtractedField",
    "ExtractedGrievanceData",
    "extract_grievance_data",
    "fallback_heuristic_extraction",
    "process_document_extraction",
]
