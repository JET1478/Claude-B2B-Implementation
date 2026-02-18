"""Authentication middleware - simple API key + admin JWT auth."""

from datetime import datetime, timedelta

from fastapi import HTTPException, Security, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_admin_token(email: str) -> str:
    """Create a JWT token for admin access."""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": email, "exp": expire, "type": "admin"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify admin JWT token. Returns admin email."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def verify_webhook_tenant(
    x_tenant_slug: str = Header(..., description="Tenant slug for webhook routing"),
    x_api_key: str = Header(None, description="Optional API key for webhook auth"),
) -> str:
    """Extract and validate tenant slug from webhook headers.
    Returns the tenant slug; actual tenant lookup happens in the endpoint.
    """
    if not x_tenant_slug:
        raise HTTPException(status_code=400, detail="X-Tenant-Slug header required")
    return x_tenant_slug
