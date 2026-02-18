"""Run history and ticket/lead detail endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import verify_admin_token
from app.models.run import Run
from app.models.ticket import Ticket
from app.models.lead import Lead
from app.schemas.common import RunResponse, TicketResponse, LeadResponse, UsageStats
from app.services.budget import BudgetEnforcer

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[RunResponse])
async def list_runs(
    tenant_id: UUID | None = None,
    workflow: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List pipeline runs with optional filters."""
    query = select(Run).order_by(Run.created_at.desc())
    if tenant_id:
        query = query.where(Run.tenant_id == tenant_id)
    if workflow:
        query = query.where(Run.workflow == workflow)
    if status:
        query = query.where(Run.status == status)
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    runs = result.scalars().all()
    return [RunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Get a single run by ID."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse.model_validate(run)


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    tenant_id: UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List support tickets."""
    query = select(Ticket).order_by(Ticket.created_at.desc())
    if tenant_id:
        query = query.where(Ticket.tenant_id == tenant_id)
    if status:
        query = query.where(Ticket.status == status)
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    tickets = result.scalars().all()
    return [TicketResponse.model_validate(t) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Get a single ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse.model_validate(ticket)


@router.get("/leads", response_model=list[LeadResponse])
async def list_leads(
    tenant_id: UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List sales leads."""
    query = select(Lead).order_by(Lead.created_at.desc())
    if tenant_id:
        query = query.where(Lead.tenant_id == tenant_id)
    if status:
        query = query.where(Lead.status == status)
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    leads = result.scalars().all()
    return [LeadResponse.model_validate(l) for l in leads]


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Get a single lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.get("/usage/{tenant_id}", response_model=dict)
async def get_usage(
    tenant_id: UUID,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage stats for a tenant (from Redis)."""
    from app.models.tenant import Tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    enforcer = BudgetEnforcer(
        str(tenant.id), tenant.max_runs_per_day,
        tenant.max_tokens_per_day, tenant.max_items_per_minute,
    )
    return enforcer.get_usage()
