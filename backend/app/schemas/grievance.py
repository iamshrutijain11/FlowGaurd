import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import GrievanceStage


def _aware(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


class GrievanceCreate(BaseModel):
    complaint_id: str = Field(min_length=1, max_length=100, examples=["CMP-2026-001"])
    entity_name: str = Field(min_length=1, max_length=255, examples=["Demo Brokerage Pvt Ltd"])
    issue_type: str = Field(min_length=1, max_length=255, examples=["Transaction related issue"])
    issue_description: str = Field(default="", max_length=10000)
    submission_date: datetime
    acknowledgement_date: datetime | None = Field(
        default=None, description="If known. Records an ACKNOWLEDGED event."
    )
    current_stage: GrievanceStage | None = Field(
        default=None,
        description="Current status if known. Defaults to FILED (or ACKNOWLEDGED if an acknowledgement date is given).",
    )

    @field_validator("complaint_id", "entity_name", "issue_type")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("submission_date", "acknowledgement_date")
    @classmethod
    def _tz(cls, v):
        return _aware(v)

    @model_validator(mode="after")
    def _ack_after_submission(self):
        if self.acknowledgement_date and self.acknowledgement_date < self.submission_date:
            raise ValueError("acknowledgement_date cannot be earlier than submission_date")
        return self


class GrievanceUpdate(BaseModel):
    """Partial update. Stage changes are recorded as timeline events; complaint_id is immutable."""

    entity_name: str | None = Field(default=None, min_length=1, max_length=255)
    issue_type: str | None = Field(default=None, min_length=1, max_length=255)
    issue_description: str | None = Field(default=None, max_length=10000)
    current_stage: GrievanceStage | None = None


class WarningOut(BaseModel):
    """FlowGuard-generated observation (NOT a regulatory conclusion)."""

    type: str
    severity: str = "WARNING"
    rule: str | None = None
    reason: str | None = None
    triggered_at: datetime
    event_id: uuid.UUID
    based_on_event: str | None = None


class GrievanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: str
    entity_name: str
    issue_type: str
    issue_description: str
    submission_date: datetime
    current_stage: GrievanceStage
    status_updated_at: datetime
    created_at: datetime
    updated_at: datetime
    # Derived (warnings are stored separately from the grievance stage)
    warning: WarningOut | None = None
    last_event_at: datetime | None = None


class DashboardSummary(BaseModel):
    active: int
    on_track: int
    potentially_delayed: int
    resolved: int


class NextActionOut(BaseModel):
    type: str = Field(description="NO_ACTION | FOLLOW_UP | REVIEW_DOCUMENTS | FURTHER_ACTION_AVAILABLE")
    title: str
    description: str
    required_documents: list[str] = []
    official_source: str | None = Field(
        default=None, description="Verified official guidance source (string name and URL or null)."
    )
    escalation_path: str | None = None
    conditions: list[str] = []
    disclaimer: str | None = None
    guidance_notes: str | None = None
    is_placeholder: bool = True

    @field_validator("official_source", mode="before")
    @classmethod
    def _coerce_official_source(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, dict):
            portal = v.get("official_portal")
            path = v.get("escalation_path")
            if path and portal:
                return f"{path} ({portal})"
            return portal or path or str(v)
        return str(v)

    @field_validator("conditions", mode="before")
    @classmethod
    def _coerce_conditions(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return [str(v)]

    @field_validator("required_documents", mode="before")
    @classmethod
    def _coerce_required_docs(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return [str(v)]

    @field_validator("escalation_path", "disclaimer", "guidance_notes", mode="before")
    @classmethod
    def _coerce_str_or_none(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return ", ".join(f"{k}: {val}" for k, val in v.items())
        return str(v)


class ExplanationOut(BaseModel):
    current_situation: str
    timeline_summary: str
    warning_explanation: str | None = None
    missing_information: list[str] = []
    next_step_summary: str
    generated_at: datetime
    is_placeholder: bool = True

    @field_validator("missing_information", mode="before")
    @classmethod
    def _coerce_missing_info(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        if isinstance(v, dict):
            return [f"{k}: {val}" for k, val in v.items()]
        return [str(v)]

    @field_validator("current_situation", "timeline_summary", "next_step_summary", mode="before")
    @classmethod
    def _coerce_string(cls, v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return str(v)
        return str(v)

    @field_validator("warning_explanation", mode="before")
    @classmethod
    def _coerce_warning_exp(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return str(v)
        return str(v)
