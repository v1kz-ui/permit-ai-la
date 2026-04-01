"""Admin API endpoints -- staff/admin only."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.audit_log import AuditLog
from app.models.clearance import Clearance
from app.models.project import Project
from app.models.user import User
from app.schemas.common import ClearanceStatus, UserRole
from app.services import audit_service

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_staff(current_user) -> None:
    """Raise 403 unless the caller is staff or admin."""
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: UserRole | None = None,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)

    query = select(User)
    if role:
        query = query.where(User.role == role)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * size).limit(size).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size else 0,
    }


@router.patch("/users/{user_id}/role")
async def change_user_role(
    user_id: UUID,
    role: UserRole,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    user.role = role.value

    await audit_service.log_action(
        db,
        table_name="users",
        record_id=str(user_id),
        action="UPDATE",
        old_value={"role": old_role},
        new_value={"role": role.value},
        changed_by=current_user.id,
        field_name="role",
    )

    await db.flush()
    await db.refresh(user)
    return {"id": str(user.id), "email": user.email, "role": user.role}


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------

@router.get("/audit")
async def system_audit(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    table_name: str | None = None,
    user_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)

    rows = await audit_service.get_system_audit(
        db,
        start_date=start_date,
        end_date=end_date,
        table_filter=table_name,
        user_filter=user_id,
        limit=size,
        offset=(page - 1) * size,
    )

    return {
        "items": [
            {
                "id": str(r.id),
                "table_name": r.table_name,
                "record_id": r.record_id,
                "action": r.action,
                "field_name": r.field_name,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "changed_by": str(r.changed_by) if r.changed_by else None,
                "changed_at": r.changed_at.isoformat(),
            }
            for r in rows
        ],
        "page": page,
        "size": size,
    }


@router.get("/audit/{record_id}")
async def record_audit_trail(
    record_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)

    rows = await audit_service.get_audit_trail(db, record_id=record_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "table_name": r.table_name,
            "record_id": r.record_id,
            "action": r.action,
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "changed_by": str(r.changed_by) if r.changed_by else None,
            "changed_at": r.changed_at.isoformat(),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

@router.post("/bulk-update-clearances")
async def bulk_update_clearances(
    updates: list[dict],
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Bulk update clearance statuses.

    Expected body: [{"clearance_id": "...", "status": "approved"}, ...]
    """
    _require_staff(current_user)

    results = []
    for item in updates:
        cid = item.get("clearance_id")
        new_status = item.get("status")
        if not cid or not new_status:
            results.append({"clearance_id": cid, "success": False, "error": "Missing clearance_id or status"})
            continue

        try:
            status_enum = ClearanceStatus(new_status)
        except ValueError:
            results.append({"clearance_id": cid, "success": False, "error": f"Invalid status: {new_status}"})
            continue

        res = await db.execute(select(Clearance).where(Clearance.id == UUID(cid)))
        clearance = res.scalar_one_or_none()
        if not clearance:
            results.append({"clearance_id": cid, "success": False, "error": "Not found"})
            continue

        old_status = clearance.status
        clearance.status = status_enum.value

        await audit_service.log_action(
            db,
            table_name="clearances",
            record_id=cid,
            action="UPDATE",
            old_value={"status": old_status},
            new_value={"status": status_enum.value},
            changed_by=current_user.id,
            field_name="status",
        )

        results.append({"clearance_id": cid, "success": True, "new_status": status_enum.value})

    await db.flush()
    return {"updated": len([r for r in results if r.get("success")]), "results": results}


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------

@router.get("/system-health")
async def system_health(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)

    health: dict = {"status": "ok"}

    # Database connectivity
    try:
        await db.execute(select(func.count()).select_from(Project))
        health["database"] = {"status": "connected"}
    except Exception as e:
        health["database"] = {"status": "error", "detail": str(e)}

    # Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        info = await r.info("memory")
        health["redis"] = {
            "status": "connected",
            "used_memory_human": info.get("used_memory_human", "unknown"),
        }
        await r.aclose()
    except Exception as e:
        health["redis"] = {"status": "unavailable", "detail": str(e)}

    # Pipeline queue depth (approximate via pending clearances)
    try:
        pending_count = (await db.execute(
            text("SELECT COUNT(*) FROM clearances WHERE status IN ('not_started', 'in_review')")
        )).scalar() or 0
        health["queue_depth"] = pending_count
    except Exception:
        health["queue_depth"] = None

    # Active projects count
    try:
        active_count = (await db.execute(
            text("SELECT COUNT(*) FROM projects WHERE status NOT IN ('closed', 'final')")
        )).scalar() or 0
        health["active_projects"] = active_count
    except Exception:
        health["active_projects"] = None

    return health


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

@router.delete("/cache")
async def clear_cache(
    pattern: str | None = None,
    current_user=Depends(get_current_user),
):
    """Clear Redis cache. If pattern provided, delete matching keys; otherwise flush all."""
    _require_staff(current_user)

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)

        if pattern:
            keys = []
            async for key in r.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await r.delete(*keys)
            deleted = len(keys)
        else:
            await r.flushdb()
            deleted = -1  # indicates full flush

        await r.aclose()
        return {"cleared": True, "deleted_keys": deleted}
    except Exception as e:
        logger.error("cache_clear_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")
