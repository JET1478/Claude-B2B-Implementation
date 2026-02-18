"""Audit log viewer endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import verify_admin_token
from app.models.audit import AuditLog
from app.schemas.common import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    tenant_id: UUID | None = None,
    run_id: UUID | None = None,
    action: str | None = None,
    workflow: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    admin: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs with filters."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)
    if run_id:
        query = query.where(AuditLog.run_id == run_id)
    if action:
        query = query.where(AuditLog.action == action)
    if workflow:
        query = query.where(AuditLog.workflow == workflow)

    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    logs = result.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]
