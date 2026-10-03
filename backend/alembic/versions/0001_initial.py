"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-03
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _enum(name: str, length: int, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=length, validate_strings=True)


STAGES = ("FILED", "ACKNOWLEDGED", "AWAITING_RESPONSE", "RESPONSE_RECEIVED", "RESOLVED", "FURTHER_ACTION")
EVENT_TYPES = STAGES + (
    "POTENTIAL_DELAY", "MISSING_INFORMATION", "FOLLOW_UP_DUE", "DOCUMENT_REQUIRED", "NO_RECENT_UPDATE",
    "REMINDER", "DOCUMENT_UPLOADED", "EXTRACTION_COMPLETED", "DETAILS_UPDATED", "NOTE_ADDED", "FOLLOW_UP_SENT",
)
ACTIONS = ("NO_ACTION", "FOLLOW_UP", "REVIEW_DOCUMENTS", "FURTHER_ACTION_AVAILABLE")


def _ts(name: str, **kw) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), **kw)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("preferred_language", sa.String(8), nullable=False, server_default="en"),
        _ts("created_at", nullable=False, server_default=sa.func.now()),
        _ts("updated_at", nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "grievances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("complaint_id", sa.String(100), nullable=False),
        sa.Column("entity_name", sa.String(255), nullable=False),
        sa.Column("issue_type", sa.String(255), nullable=False),
        sa.Column("issue_description", sa.Text(), nullable=False, server_default=""),
        _ts("submission_date", nullable=False),
        sa.Column("current_stage", _enum("grievance_stage", 32, *STAGES), nullable=False),
        _ts("status_updated_at", nullable=False),
        _ts("created_at", nullable=False, server_default=sa.func.now()),
        _ts("updated_at", nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "complaint_id", name="uq_grievance_user_complaint"),
    )
    op.create_index("ix_grievances_user_id", "grievances", ["user_id"])
    op.create_index("ix_grievances_current_stage", "grievances", ["current_stage"])

    op.create_table(
        "grievance_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("grievance_id", sa.Uuid(), sa.ForeignKey("grievances.id"), nullable=False),
        sa.Column("event_type", _enum("event_type", 32, *EVENT_TYPES), nullable=False),
        _ts("event_time", nullable=False),
        sa.Column("source", _enum("event_source", 16, "USER", "SYSTEM", "AI", "ADMIN"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        _ts("created_at", nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_grievance_events_grievance_id", "grievance_events", ["grievance_id"])
    op.create_index("ix_grievance_events_event_time", "grievance_events", ["event_time"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("grievance_id", sa.Uuid(), sa.ForeignKey("grievances.id"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column(
            "document_type",
            _enum("document_type", 32, "ACKNOWLEDGEMENT", "RESPONSE", "SCREENSHOT", "SUPPORTING_EVIDENCE", "OTHER"),
            nullable=False,
        ),
        _ts("uploaded_at", nullable=False, server_default=sa.func.now()),
        sa.Column(
            "extraction_status",
            _enum("extraction_status", 16, "PENDING", "PROCESSING", "COMPLETED", "FAILED"),
            nullable=False,
        ),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_documents_grievance_id", "documents", ["grievance_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("grievance_id", sa.Uuid(), sa.ForeignKey("grievances.id"), nullable=True),
        sa.Column(
            "notification_type",
            _enum("notification_type", 32, "STATUS_CHANGED", "POTENTIAL_DELAY", "FOLLOW_UP_DUE",
                  "DOCUMENT_REQUIRED", "GRIEVANCE_RESOLVED"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("created_at", nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "escalations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("grievance_id", sa.Uuid(), sa.ForeignKey("grievances.id"), nullable=False),
        sa.Column("escalation_type", _enum("action_type", 32, *ACTIONS), nullable=False),
        sa.Column("status", _enum("escalation_status", 16, "PENDING", "IN_PROGRESS", "COMPLETED"), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("guidance_source", sa.String(500), nullable=True),
        _ts("created_at", nullable=False, server_default=sa.func.now()),
        _ts("completed_at", nullable=True),
    )
    op.create_index("ix_escalations_grievance_id", "escalations", ["grievance_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        _ts("timestamp", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    for table in ("audit_logs", "escalations", "notifications", "documents", "grievance_events", "grievances", "users"):
        op.drop_table(table)
