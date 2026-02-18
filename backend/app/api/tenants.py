"""Tenant CRUD admin endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import verify_admin_token
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.crypto import encrypt_value

import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List all tenants (admin only)."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(per_page)
    )
    tenants = result.scalars().all()
    return [_tenant_to_response(t) for t in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Get a single tenant by ID."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_to_response(tenant)


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreate,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tenant."""
    # Check slug uniqueness
    existing = await db.execute(select(Tenant).where(Tenant.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Tenant slug '{data.slug}' already exists")

    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        allowed_domains=data.allowed_domains,
        max_runs_per_day=data.max_runs_per_day,
        max_tokens_per_day=data.max_tokens_per_day,
        max_items_per_minute=data.max_items_per_minute,
        support_workflow_enabled=data.support_workflow_enabled,
        sales_workflow_enabled=data.sales_workflow_enabled,
        autosend_enabled=data.autosend_enabled,
        confidence_threshold=data.confidence_threshold,
        slack_webhook_url=data.slack_webhook_url,
        support_config_yaml=data.support_config_yaml,
        sales_config_yaml=data.sales_config_yaml,
    )

    # Encrypt API key if provided
    if data.anthropic_api_key:
        tenant.anthropic_api_key_encrypted = encrypt_value(data.anthropic_api_key)

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    logger.info("tenant_created", slug=tenant.slug, id=str(tenant.id))
    return _tenant_to_response(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Update a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle API key encryption
    if "anthropic_api_key" in update_data:
        key = update_data.pop("anthropic_api_key")
        if key:
            tenant.anthropic_api_key_encrypted = encrypt_value(key)
        else:
            tenant.anthropic_api_key_encrypted = None

    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    logger.info("tenant_updated", slug=tenant.slug)
    return _tenant_to_response(tenant)


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: UUID,
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a tenant (deactivate)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.is_active = False
    await db.commit()
    logger.info("tenant_deactivated", slug=tenant.slug)


def _tenant_to_response(tenant: Tenant) -> TenantResponse:
    """Convert tenant model to response, masking sensitive fields."""
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        allowed_domains=tenant.allowed_domains,
        is_active=tenant.is_active,
        has_anthropic_key=bool(tenant.anthropic_api_key_encrypted),
        max_runs_per_day=tenant.max_runs_per_day,
        max_tokens_per_day=tenant.max_tokens_per_day,
        max_items_per_minute=tenant.max_items_per_minute,
        support_workflow_enabled=tenant.support_workflow_enabled,
        sales_workflow_enabled=tenant.sales_workflow_enabled,
        autosend_enabled=tenant.autosend_enabled,
        confidence_threshold=tenant.confidence_threshold,
        slack_webhook_url=tenant.slack_webhook_url,
        support_config_yaml=tenant.support_config_yaml,
        sales_config_yaml=tenant.sales_config_yaml,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )
