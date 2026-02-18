"""Webhook intake endpoints for support tickets and sales leads."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis
from rq import Queue

from app.database import get_db
from app.config import settings
from app.models.tenant import Tenant
from app.models.ticket import Ticket
from app.models.lead import Lead
from app.models.run import Run
from app.models.audit import AuditLog
from app.schemas.webhook import SupportWebhookPayload, LeadWebhookPayload, WebhookResponse
from app.services.budget import BudgetEnforcer, BudgetExceededError, CircuitOpenError
from app.api.health import WEBHOOK_REQUESTS, ERRORS

import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _resolve_tenant(db: AsyncSession, slug: str) -> Tenant:
    """Look up active tenant by slug."""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{slug}' not found or inactive")
    return tenant


def _get_queue(name: str = "default") -> Queue:
    """Get an RQ queue."""
    from app.services.budget import get_redis
    return Queue(name, connection=get_redis())


@router.post("/support", response_model=WebhookResponse)
async def ingest_support_ticket(
    payload: SupportWebhookPayload,
    x_tenant_slug: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a support ticket via webhook and queue for triage."""
    tenant = await _resolve_tenant(db, x_tenant_slug)
    WEBHOOK_REQUESTS.labels(workflow="support", tenant=tenant.slug).inc()

    if not tenant.support_workflow_enabled:
        raise HTTPException(status_code=403, detail="Support workflow disabled for this tenant")

    # Budget check
    try:
        enforcer = BudgetEnforcer(
            str(tenant.id), tenant.max_runs_per_day,
            tenant.max_tokens_per_day, tenant.max_items_per_minute,
        )
        enforcer.check_all()
    except (BudgetExceededError, CircuitOpenError) as e:
        ERRORS.labels(type="budget").inc()
        raise HTTPException(status_code=429, detail=str(e))

    # Create run record
    run_id = uuid.uuid4()
    run = Run(
        id=run_id,
        tenant_id=tenant.id,
        workflow="support_triage",
        status="queued",
    )
    db.add(run)

    # Create ticket record
    ticket_id = uuid.uuid4()
    ticket = Ticket(
        id=ticket_id,
        tenant_id=tenant.id,
        external_id=payload.external_id,
        source=payload.source,
        from_email=payload.from_email,
        from_name=payload.from_name,
        subject=payload.subject,
        body=payload.body,
        attachments_meta=payload.attachments,
        status="new",
        run_id=run_id,
    )
    db.add(ticket)

    # Audit log
    audit = AuditLog(
        tenant_id=tenant.id,
        run_id=run_id,
        action="ticket_created",
        workflow="support_triage",
        step="intake",
        input_summary=f"Subject: {payload.subject or 'N/A'}, From: {payload.from_email or 'N/A'}",
        actor="webhook",
    )
    db.add(audit)

    await db.commit()

    # Enqueue worker task
    try:
        q = _get_queue("support")
        q.enqueue(
            "app.workers.support_triage.process_support_ticket",
            str(tenant.id), str(ticket_id), str(run_id),
            job_timeout=300,
            retry={"max": 3, "interval": [10, 30, 60]},
        )
        enforcer.increment_rate()
        enforcer.increment_daily_runs()
    except Exception as e:
        logger.error("failed_to_enqueue_support_task", error=str(e))
        ERRORS.labels(type="queue").inc()

    logger.info("support_ticket_ingested",
                tenant=tenant.slug, ticket_id=str(ticket_id), run_id=str(run_id))

    return WebhookResponse(
        ok=True,
        id=str(ticket_id),
        message="Support ticket queued for triage",
    )


@router.post("/leads", response_model=WebhookResponse)
async def ingest_sales_lead(
    payload: LeadWebhookPayload,
    x_tenant_slug: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a sales lead via webhook and queue for qualification."""
    tenant = await _resolve_tenant(db, x_tenant_slug)
    WEBHOOK_REQUESTS.labels(workflow="leads", tenant=tenant.slug).inc()

    if not tenant.sales_workflow_enabled:
        raise HTTPException(status_code=403, detail="Sales workflow disabled for this tenant")

    # Budget check
    try:
        enforcer = BudgetEnforcer(
            str(tenant.id), tenant.max_runs_per_day,
            tenant.max_tokens_per_day, tenant.max_items_per_minute,
        )
        enforcer.check_all()
    except (BudgetExceededError, CircuitOpenError) as e:
        ERRORS.labels(type="budget").inc()
        raise HTTPException(status_code=429, detail=str(e))

    # Create run record
    run_id = uuid.uuid4()
    run = Run(
        id=run_id,
        tenant_id=tenant.id,
        workflow="lead_qualify",
        status="queued",
    )
    db.add(run)

    # Create lead record
    lead_id = uuid.uuid4()
    lead = Lead(
        id=lead_id,
        tenant_id=tenant.id,
        source=payload.source,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        name=payload.name,
        email=payload.email,
        company=payload.company,
        phone=payload.phone,
        message=payload.message,
        status="new",
        run_id=run_id,
    )
    db.add(lead)

    # Audit log
    audit = AuditLog(
        tenant_id=tenant.id,
        run_id=run_id,
        action="lead_created",
        workflow="lead_qualify",
        step="intake",
        input_summary=f"Name: {payload.name}, Email: {payload.email}, Company: {payload.company or 'N/A'}",
        actor="webhook",
    )
    db.add(audit)

    await db.commit()

    # Enqueue worker task
    try:
        q = _get_queue("leads")
        q.enqueue(
            "app.workers.lead_qualify.process_lead",
            str(tenant.id), str(lead_id), str(run_id),
            job_timeout=300,
            retry={"max": 3, "interval": [10, 30, 60]},
        )
        enforcer.increment_rate()
        enforcer.increment_daily_runs()
    except Exception as e:
        logger.error("failed_to_enqueue_lead_task", error=str(e))
        ERRORS.labels(type="queue").inc()

    logger.info("lead_ingested",
                tenant=tenant.slug, lead_id=str(lead_id), run_id=str(run_id))

    return WebhookResponse(
        ok=True,
        id=str(lead_id),
        message="Lead queued for qualification",
    )
