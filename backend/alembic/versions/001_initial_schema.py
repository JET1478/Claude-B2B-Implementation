"""Initial schema with all core tables.

Revision ID: 001
Revises: None
Create Date: 2025-01-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("allowed_domains", sa.Text, server_default=""),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("anthropic_api_key_encrypted", sa.Text, nullable=True),
        sa.Column("max_runs_per_day", sa.Integer, server_default="500"),
        sa.Column("max_tokens_per_day", sa.Integer, server_default="500000"),
        sa.Column("max_items_per_minute", sa.Integer, server_default="10"),
        sa.Column("support_workflow_enabled", sa.Boolean, server_default="true"),
        sa.Column("sales_workflow_enabled", sa.Boolean, server_default="true"),
        sa.Column("autosend_enabled", sa.Boolean, server_default="false"),
        sa.Column("confidence_threshold", sa.Float, server_default="0.85"),
        sa.Column("support_config_yaml", sa.Text, nullable=True),
        sa.Column("sales_config_yaml", sa.Text, nullable=True),
        sa.Column("slack_webhook_url", sa.Text, nullable=True),
        sa.Column("hubspot_api_key_encrypted", sa.Text, nullable=True),
        sa.Column("smtp_config_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # Runs
    op.create_table(
        "runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("workflow", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("ticket_id", UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", UUID(as_uuid=True), nullable=True),
        sa.Column("local_model_calls", sa.Integer, server_default="0"),
        sa.Column("local_model_tokens", sa.Integer, server_default="0"),
        sa.Column("claude_calls", sa.Integer, server_default="0"),
        sa.Column("claude_input_tokens", sa.Integer, server_default="0"),
        sa.Column("claude_output_tokens", sa.Integer, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float, server_default="0"),
        sa.Column("steps_completed", JSONB, nullable=True),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_runs_tenant_id", "runs", ["tenant_id"])

    # Tickets
    op.create_table(
        "tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), server_default="webhook"),
        sa.Column("from_email", sa.String(255), nullable=True),
        sa.Column("from_name", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("attachments_meta", JSONB, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("suggested_team", sa.String(100), nullable=True),
        sa.Column("needs_human", sa.Boolean, nullable=True),
        sa.Column("classification_confidence", sa.Float, nullable=True),
        sa.Column("classification_raw", JSONB, nullable=True),
        sa.Column("draft_reply", sa.Text, nullable=True),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.Column("recommended_action", sa.String(255), nullable=True),
        sa.Column("follow_up_questions", JSONB, nullable=True),
        sa.Column("assigned_team", sa.String(100), nullable=True),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("sla_due_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(30), server_default="new"),
        sa.Column("reply_sent", sa.Boolean, server_default="false"),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_tickets_tenant_id", "tickets", ["tenant_id"])

    # Leads
    op.create_table(
        "leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source", sa.String(50), server_default="webhook"),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_medium", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("company_size_cue", sa.String(50), nullable=True),
        sa.Column("intent_classification", sa.String(100), nullable=True),
        sa.Column("urgency", sa.String(20), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("spam_score", sa.Float, nullable=True),
        sa.Column("extraction_confidence", sa.Float, nullable=True),
        sa.Column("extraction_raw", JSONB, nullable=True),
        sa.Column("qualification_summary", sa.Text, nullable=True),
        sa.Column("follow_up_questions", JSONB, nullable=True),
        sa.Column("suggested_next_step", sa.String(100), nullable=True),
        sa.Column("crm_contact_id", sa.String(255), nullable=True),
        sa.Column("crm_deal_id", sa.String(255), nullable=True),
        sa.Column("email_drafts", JSONB, nullable=True),
        sa.Column("follow_up_scheduled_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(30), server_default="new"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_email", "leads", ["email"])

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("workflow", sa.String(50), nullable=True),
        sa.Column("step", sa.String(100), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("prompt_template_id", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("estimated_cost_usd", sa.Float, nullable=True),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("reason_code", sa.String(100), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("actor", sa.String(100), server_default="system"),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_run_id", "audit_logs", ["run_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("leads")
    op.drop_table("tickets")
    op.drop_table("runs")
    op.drop_table("tenants")
