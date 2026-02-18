"""Tenant resolution middleware."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant:
    """Resolve tenant by slug. Raises 404 if not found or inactive."""
    result = await db.execute(select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{slug}' not found or inactive")
    return tenant


async def get_tenant_by_id(db: AsyncSession, tenant_id: UUID) -> Tenant:
    """Resolve tenant by ID."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
