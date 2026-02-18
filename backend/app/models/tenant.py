"""Tenant model - multi-tenant configuration."""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    allowed_domains: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # BYOK - encrypted Anthropic API key
    anthropic_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Usage limits
    max_runs_per_day: Mapped[int] = mapped_column(Integer, default=500)
    max_tokens_per_day: Mapped[int] = mapped_column(Integer, default=500000)
    max_items_per_minute: Mapped[int] = mapped_column(Integer, default=10)

    # Workflow toggles
    support_workflow_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sales_workflow_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Safety
    autosend_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.85)

    # YAML config (stored as text, parsed as YAML)
    support_config_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_config_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Integration settings (JSON-encoded)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hubspot_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
