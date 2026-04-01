"""Monitoring and health-check endpoints."""

import sqlalchemy
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.monitoring import get_health_details, get_metrics, get_metrics_prometheus
from app.core.redis import get_redis

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Return application metrics in Prometheus text exposition format."""
    return get_metrics_prometheus()


@router.get("/health/detailed")
async def health_detailed(
    db: AsyncSession = Depends(get_db_session),
):
    """Extended health check with DB, Redis, and system details."""
    details = await get_health_details()

    # DB connectivity
    try:
        await db.execute(sqlalchemy.text("SELECT 1"))
        details["database_connectivity"] = "healthy"
    except Exception as exc:
        details["database_connectivity"] = f"unhealthy: {exc}"

    # Overall metrics snapshot
    metrics_snapshot = get_metrics()
    details["total_requests"] = metrics_snapshot["total_requests"]
    details["total_errors"] = metrics_snapshot["total_errors"]
    details["global_p99_ms"] = metrics_snapshot["global_p99_ms"]

    return details


@router.get("/health/ready")
async def health_ready(
    db: AsyncSession = Depends(get_db_session),
):
    """Readiness probe: is the app ready to serve traffic?"""
    checks: dict[str, str] = {}

    # Database readiness
    try:
        await db.execute(sqlalchemy.text("SELECT 1"))
        checks["database"] = "ready"
    except Exception as exc:
        checks["database"] = f"not_ready: {exc}"

    # Redis readiness
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ready"
    except Exception as exc:
        checks["redis"] = f"not_ready: {exc}"

    all_ready = all(v == "ready" for v in checks.values())
    status_code = 200 if all_ready else 503
    return {
        "ready": all_ready,
        "checks": checks,
    } | ({"_status": status_code} if not all_ready else {})


@router.get("/health/live")
async def health_live():
    """Liveness probe: is the app process alive?"""
    return {"alive": True}
