"""Audit log model - tracks every action with full context."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g.: ticket_created, classified, draft_generated, email_sent, lead_created,
    #       lead_qualified, crm_updated, notification_sent, budget_exceeded, error

    workflow: Mapped[str | None] = mapped_column(String(50), nullable=True)
    step: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Model tracking
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)  # local_7b, claude-sonnet, etc.
    prompt_template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(default=None)
    output_tokens: Mapped[int | None] = mapped_column(default=None)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Content (redacted if needed)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Actor
    actor: Mapped[str] = mapped_column(String(100), default="system")  # system, admin, webhook

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
