"""Staff dashboard API endpoints.

Provides aggregate analytics, department workload, and bottleneck data
for city staff to monitor the fire-rebuild permit pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.clearance import Clearance
from app.models.project import Project

router = APIRouter(prefix="/staff", tags=["staff"])


def _require_staff(current_user):
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Staff access required")


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Aggregate stats for the staff dashboard homepage."""
    _require_staff(current_user)

    # Active projects count
    active_count = (await db.execute(
        select(func.count(Project.id)).where(
            Project.status.notin_(["closed", "final"])
        )
    )).scalar() or 0

    # Pending clearances count
    pending_count = (await db.execute(
        select(func.count(Clearance.id)).where(
            Clearance.status.in_(["not_started", "in_review"])
        )
    )).scalar() or 0

    # Bottleneck count
    bottleneck_count = (await db.execute(
        select(func.count(Clearance.id)).where(Clearance.is_bottleneck.is_(True))
    )).scalar() or 0

    # Average predicted days
    avg_days = (await db.execute(
        select(func.avg(Project.predicted_days_to_issue)).where(
            Project.predicted_days_to_issue.isnot(None)
        )
    )).scalar()

    # Projects by pathway
    pathway_counts = (await db.execute(
        select(Project.pathway, func.count(Project.id))
        .group_by(Project.pathway)
    )).all()

    # Projects by status
    status_counts = (await db.execute(
        select(Project.status, func.count(Project.id))
        .group_by(Project.status)
    )).all()

    return {
        "active_projects": active_count,
        "pending_clearances": pending_count,
        "bottlenecks": bottleneck_count,
        "avg_days_to_issue": round(avg_days, 1) if avg_days else None,
        "projects_by_pathway": {str(p): c for p, c in pathway_counts},
        "projects_by_status": {str(s): c for s, c in status_counts},
    }


@router.get("/dashboard/department-workload")
async def get_department_workload(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Clearance workload breakdown by department."""
    _require_staff(current_user)

    results = (await db.execute(
        select(
            Clearance.department,
            Clearance.status,
            func.count(Clearance.id),
        )
        .group_by(Clearance.department, Clearance.status)
        .order_by(Clearance.department)
    )).all()

    departments: dict[str, dict] = {}
    for dept, status, count in results:
        dept_str = str(dept)
        if dept_str not in departments:
            departments[dept_str] = {
                "department": dept_str,
                "total": 0,
                "not_started": 0,
                "in_review": 0,
                "approved": 0,
                "conditional": 0,
                "denied": 0,
            }
        departments[dept_str]["total"] += count
        departments[dept_str][str(status)] = count

    return {"departments": list(departments.values())}


@router.get("/dashboard/bottlenecks")
async def get_bottlenecks(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Get all flagged bottleneck clearances with project context."""
    _require_staff(current_user)

    result = await db.execute(
        select(Clearance, Project.address, Project.pathway)
        .join(Project, Clearance.project_id == Project.id)
        .where(Clearance.is_bottleneck.is_(True))
        .where(Clearance.status.in_(["not_started", "in_review"]))
        .order_by(Clearance.predicted_days.desc())
    )
    rows = result.all()

    bottlenecks = []
    for clearance, address, pathway in rows:
        bottlenecks.append({
            "clearance_id": str(clearance.id),
            "project_id": str(clearance.project_id),
            "address": address,
            "pathway": str(pathway),
            "department": str(clearance.department),
            "clearance_type": clearance.clearance_type,
            "status": str(clearance.status),
            "predicted_days": clearance.predicted_days,
            "submitted_date": clearance.submitted_date.isoformat() if clearance.submitted_date else None,
        })

    return {"bottlenecks": bottlenecks, "count": len(bottlenecks)}


@router.get("/dashboard/kanban")
async def get_kanban_view(
    department: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Kanban board view of clearances grouped by status.

    Used by the staff dashboard to show clearance pipeline.
    """
    _require_staff(current_user)

    query = (
        select(Clearance, Project.address)
        .join(Project, Clearance.project_id == Project.id)
        .where(Project.status.notin_(["closed", "final"]))
    )

    if department:
        query = query.where(Clearance.department == department)

    query = query.order_by(Clearance.created_at)
    result = await db.execute(query)
    rows = result.all()

    columns = {
        "not_started": [],
        "in_review": [],
        "approved": [],
        "conditional": [],
        "denied": [],
    }

    for clearance, address in rows:
        status_key = str(clearance.status)
        if status_key in columns:
            columns[status_key].append({
                "clearance_id": str(clearance.id),
                "project_id": str(clearance.project_id),
                "address": address,
                "department": str(clearance.department),
                "clearance_type": clearance.clearance_type,
                "is_bottleneck": clearance.is_bottleneck,
                "predicted_days": clearance.predicted_days,
                "assigned_to": clearance.assigned_to,
                "submitted_date": clearance.submitted_date.isoformat() if clearance.submitted_date else None,
            })

    return {
        "columns": columns,
        "total": sum(len(v) for v in columns.values()),
    }


@router.get("/dashboard/projects")
async def list_all_projects(
    status: str | None = None,
    pathway: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Staff view of all projects (no owner restriction)."""
    _require_staff(current_user)

    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    if pathway:
        query = query.where(Project.pathway == pathway)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "address": p.address,
                "apn": p.apn,
                "pathway": str(p.pathway),
                "status": str(p.status),
                "predicted_days": p.predicted_days_to_issue,
                "created_at": p.created_at.isoformat(),
                "is_coastal": p.is_coastal_zone,
                "is_hillside": p.is_hillside,
            }
            for p in projects
        ],
        "total": total,
        "page": page,
        "size": size,
    }
