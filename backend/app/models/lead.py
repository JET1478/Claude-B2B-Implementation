"""Sales lead model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Source fields
    source: Mapped[str] = mapped_column(String(50), default="webhook")  # webhook, form, api
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contact info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extraction (filled by 7B model)
    company_size_cue: Mapped[str | None] = mapped_column(String(50), nullable=True)  # startup, smb, mid, enterprise
    intent_classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low, medium, high
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Qualification (filled by Claude)
    qualification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list of strings
    suggested_next_step: Mapped[str | None] = mapped_column(String(100), nullable=True)  # call, demo, email

    # CRM
    crm_contact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_deal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Follow-up
    email_drafts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list of {subject, body}
    follow_up_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(30), default="new")  # new, processing, qualified, disqualified, contacted
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100 lead score

    # Metadata
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
