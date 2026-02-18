"""Pipeline run tracking model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Run info
    workflow: Mapped[str] = mapped_column(String(50), nullable=False)  # support_triage, lead_qualify
    status: Mapped[str] = mapped_column(String(30), default="queued")  # queued, running, completed, failed, cancelled
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # References
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Model usage tracking
    local_model_calls: Mapped[int] = mapped_column(Integer, default=0)
    local_model_tokens: Mapped[int] = mapped_column(Integer, default=0)
    claude_calls: Mapped[int] = mapped_column(Integer, default=0)
    claude_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    claude_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Step tracking
    steps_completed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list of step records
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
