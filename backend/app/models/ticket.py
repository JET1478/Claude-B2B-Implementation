"""Support ticket model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Source fields
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="webhook")  # webhook, email, api
    from_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Classification (filled by 7B model)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low, medium, high, critical
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)  # positive, neutral, negative
    suggested_team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    needs_human: Mapped[bool | None] = mapped_column(default=None)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Draft reply (filled by Claude)
    draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    follow_up_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Routing
    assigned_team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list of strings
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(30), default="new")  # new, processing, draft_ready, sent, escalated, closed
    reply_sent: Mapped[bool] = mapped_column(default=False)

    # Metadata
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
