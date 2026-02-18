"""Health check and metrics endpoints."""

import redis as redis_lib
from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text

from app.config import settings
from app.database import async_session
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])

# Prometheus metrics
WEBHOOK_REQUESTS = Counter("webhook_requests_total", "Total webhook requests", ["workflow", "tenant"])
RUN_DURATION = Histogram("run_duration_seconds", "Pipeline run duration", ["workflow"])
MODEL_CALLS = Counter("model_calls_total", "Total model calls", ["model", "task_type"])
ERRORS = Counter("errors_total", "Total errors", ["type"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db_status = "ok"
    redis_status = "ok"
    model_status = "disabled"

    # Check DB
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Redis
    try:
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
    except Exception:
        redis_status = "error"

    # Check local model
    if settings.local_model_enabled:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(settings.local_model_url.replace("/completion", "/health"))
                model_status = "ok" if resp.status_code == 200 else "error"
        except Exception:
            model_status = "error"

    overall = "healthy" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        db=db_status,
        redis=redis_status,
        local_model=model_status,
    )


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
