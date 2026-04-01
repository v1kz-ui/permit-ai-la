from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.events import emit_event
from app.core.redis import get_redis
from app.middleware.auth import get_current_user
from app.models.clearance import Clearance
from app.models.project import Project
from app.schemas.clearance import ClearanceCreate, ClearanceResponse, ClearanceUpdate

router = APIRouter(prefix="/clearances", tags=["clearances"])


@router.post("", response_model=ClearanceResponse, status_code=201)
async def create_clearance(
    data: ClearanceCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    # Only staff/admin can create clearances
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    clearance = Clearance(
        project_id=data.project_id,
        department=data.department,
        clearance_type=data.clearance_type,
        status=data.status,
    )
    db.add(clearance)
    await db.flush()
    await db.refresh(clearance)
    return clearance


@router.get("", response_model=list[ClearanceResponse])
async def list_clearances(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    # Verify user has access to the project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(Clearance)
        .where(Clearance.project_id == project_id)
        .order_by(Clearance.department)
    )
    return result.scalars().all()


@router.patch("/{clearance_id}", response_model=ClearanceResponse)
async def update_clearance(
    clearance_id: UUID,
    data: ClearanceUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Clearance).where(Clearance.id == clearance_id))
    clearance = result.scalar_one_or_none()

    if clearance is None:
        raise HTTPException(status_code=404, detail="Clearance not found")

    old_status = clearance.status
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clearance, field, value)

    await db.flush()
    await db.refresh(clearance)

    # Emit event if status changed
    if "status" in update_data and update_data["status"] != old_status:
        try:
            redis = await get_redis()
            await emit_event(
                redis,
                "clearance_changed",
                {
                    "clearance_id": str(clearance.id),
                    "project_id": str(clearance.project_id),
                    "department": clearance.department,
                    "old_status": old_status,
                    "new_status": clearance.status,
                },
            )
        except Exception:
            pass  # Don't fail the update if event emission fails

    return clearance
