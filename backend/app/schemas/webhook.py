"""Webhook payload schemas."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class SupportWebhookPayload(BaseModel):
    """Incoming support ticket via webhook."""
    subject: Optional[str] = None
    body: str = Field(..., min_length=1, max_length=50000)
    from_email: Optional[str] = None  # EmailStr is too strict for webhooks
    from_name: Optional[str] = None
    external_id: Optional[str] = None
    source: str = "webhook"
    attachments: Optional[list[dict]] = None  # [{filename, size, content_type}]
    metadata: Optional[dict] = None


class LeadWebhookPayload(BaseModel):
    """Incoming sales lead via webhook."""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    company: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    source: str = "webhook"
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    metadata: Optional[dict] = None


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    ok: bool
    id: str
    message: str
