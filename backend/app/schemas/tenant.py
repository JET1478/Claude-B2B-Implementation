"""Tenant schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    allowed_domains: str = ""
    anthropic_api_key: Optional[str] = None  # Will be encrypted before storage
    max_runs_per_day: int = 500
    max_tokens_per_day: int = 500000
    max_items_per_minute: int = 10
    support_workflow_enabled: bool = True
    sales_workflow_enabled: bool = True
    autosend_enabled: bool = False
    confidence_threshold: float = 0.85
    slack_webhook_url: Optional[str] = None
    support_config_yaml: Optional[str] = None
    sales_config_yaml: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    allowed_domains: Optional[str] = None
    is_active: Optional[bool] = None
    anthropic_api_key: Optional[str] = None
    max_runs_per_day: Optional[int] = None
    max_tokens_per_day: Optional[int] = None
    max_items_per_minute: Optional[int] = None
    support_workflow_enabled: Optional[bool] = None
    sales_workflow_enabled: Optional[bool] = None
    autosend_enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = None
    slack_webhook_url: Optional[str] = None
    support_config_yaml: Optional[str] = None
    sales_config_yaml: Optional[str] = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    allowed_domains: str
    is_active: bool
    has_anthropic_key: bool  # Never expose the actual key
    max_runs_per_day: int
    max_tokens_per_day: int
    max_items_per_minute: int
    support_workflow_enabled: bool
    sales_workflow_enabled: bool
    autosend_enabled: bool
    confidence_threshold: float
    slack_webhook_url: Optional[str]
    support_config_yaml: Optional[str]
    sales_config_yaml: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
