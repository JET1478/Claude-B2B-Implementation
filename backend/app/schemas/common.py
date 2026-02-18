"""Common response schemas."""

import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class RunResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workflow: str
    status: str
    error_message: Optional[str]
    ticket_id: Optional[uuid.UUID]
    lead_id: Optional[uuid.UUID]
    local_model_calls: int
    local_model_tokens: int
    claude_calls: int
    claude_input_tokens: int
    claude_output_tokens: int
    estimated_cost_usd: float
    steps_completed: Optional[list]
    current_step: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    run_id: Optional[uuid.UUID]
    action: str
    workflow: Optional[str]
    step: Optional[str]
    model_used: Optional[str]
    prompt_template_id: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    input_summary: Optional[str]
    output_summary: Optional[str]
    reason_code: Optional[str]
    extra_data: Optional[dict]
    actor: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    external_id: Optional[str]
    source: str
    from_email: Optional[str]
    from_name: Optional[str]
    subject: Optional[str]
    body: str
    category: Optional[str]
    priority: Optional[str]
    sentiment: Optional[str]
    suggested_team: Optional[str]
    needs_human: Optional[bool]
    classification_confidence: Optional[float]
    draft_reply: Optional[str]
    internal_notes: Optional[str]
    recommended_action: Optional[str]
    assigned_team: Optional[str]
    tags: Optional[list]
    status: str
    reply_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    name: str
    email: str
    company: Optional[str]
    phone: Optional[str]
    message: Optional[str]
    company_size_cue: Optional[str]
    intent_classification: Optional[str]
    urgency: Optional[str]
    industry: Optional[str]
    spam_score: Optional[float]
    qualification_summary: Optional[str]
    follow_up_questions: Optional[list]
    suggested_next_step: Optional[str]
    crm_contact_id: Optional[str]
    crm_deal_id: Optional[str]
    email_drafts: Optional[list]
    status: str
    score: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    per_page: int


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    db: str
    redis: str
    local_model: str


class UsageStats(BaseModel):
    tenant_id: uuid.UUID
    date: str
    total_runs: int
    completed_runs: int
    failed_runs: int
    total_claude_tokens: int
    total_local_tokens: int
    estimated_cost_usd: float
