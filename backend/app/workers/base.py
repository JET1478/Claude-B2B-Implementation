"""Base worker utilities for RQ tasks."""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.tenant import Tenant
from app.models.run import Run
from app.models.audit import AuditLog
from app.services.budget import BudgetEnforcer
from app.services.router import ModelRouter

import structlog

logger = structlog.get_logger()

# Sync engine for RQ workers (RQ tasks are synchronous)
_engine = create_engine(settings.database_url_sync, pool_size=5, max_overflow=2)
SyncSession = sessionmaker(bind=_engine)


def run_async(coro):
    """Run an async coroutine from sync RQ worker context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_sync_session() -> Session:
    return SyncSession()


def load_tenant(session: Session, tenant_id: str) -> Tenant:
    """Load tenant by ID."""
    result = session.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    return tenant


def update_run_status(session: Session, run_id: str, status: str, **kwargs):
    """Update run status and optional fields."""
    result = session.execute(select(Run).where(Run.id == uuid.UUID(run_id)))
    run = result.scalar_one_or_none()
    if run:
        run.status = status
        for k, v in kwargs.items():
            if hasattr(run, k):
                setattr(run, k, v)
        session.commit()


def create_audit_entry(
    session: Session,
    tenant_id: str,
    run_id: str,
    action: str,
    workflow: str,
    step: str,
    model_used: str | None = None,
    prompt_template_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    reason_code: str | None = None,
    extra_data: dict | None = None,
):
    """Create an audit log entry."""
    entry = AuditLog(
        tenant_id=uuid.UUID(tenant_id),
        run_id=uuid.UUID(run_id),
        action=action,
        workflow=workflow,
        step=step,
        model_used=model_used,
        prompt_template_id=prompt_template_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        input_summary=input_summary[:500] if input_summary else None,
        output_summary=output_summary[:500] if output_summary else None,
        reason_code=reason_code,
        extra_data=extra_data,
        actor="worker",
    )
    session.add(entry)
    session.commit()


def create_model_router(tenant: Tenant) -> ModelRouter:
    """Create a model router for a tenant."""
    budget = BudgetEnforcer(
        str(tenant.id),
        tenant.max_runs_per_day,
        tenant.max_tokens_per_day,
        tenant.max_items_per_minute,
    )
    return ModelRouter(
        tenant_id=str(tenant.id),
        anthropic_key_encrypted=tenant.anthropic_api_key_encrypted,
        budget=budget,
    )
