"""Staff dashboard API endpoints.

Provides aggregate analytics, department workload, and bottleneck data
for city staff to monitor the fire-rebuild permit pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.clearance import Clearance
from app.models.project import Project
from app.schemas.common import ProjectStatus, ClearanceStatus

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

    # Use raw SQL to avoid enum casting issues
    active_count = (await db.execute(
        text("SELECT COUNT(*) FROM projects WHERE status NOT IN ('closed', 'final')")
    )).scalar() or 0

    pending_count = (await db.execute(
        text("SELECT COUNT(*) FROM clearances WHERE status IN ('not_started', 'in_review')")
    )).scalar() or 0

    bottleneck_count = (await db.execute(
        text("SELECT COUNT(*) FROM clearances WHERE is_bottleneck = true")
    )).scalar() or 0

    avg_days = (await db.execute(
        text("SELECT AVG(predicted_days_to_issue) FROM projects WHERE predicted_days_to_issue IS NOT NULL")
    )).scalar()

    pathway_counts = (await db.execute(
        text("SELECT pathway, COUNT(*) FROM projects GROUP BY pathway")
    )).all()

    status_counts = (await db.execute(
        text("SELECT status, COUNT(*) FROM projects GROUP BY status")
    )).all()

    return {
        "active_projects": active_count,
        "pending_clearances": pending_count,
        "bottlenecks_detected": bottleneck_count,
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
        text("SELECT department, status, COUNT(*) FROM clearances GROUP BY department, status ORDER BY department")
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
        text("""
            SELECT c.id, c.project_id, p.address, p.pathway, c.department,
                   c.clearance_type, c.status, c.predicted_days, c.submitted_date
            FROM clearances c
            JOIN projects p ON c.project_id = p.id
            WHERE c.is_bottleneck = true AND c.status IN ('not_started', 'in_review')
            ORDER BY c.predicted_days DESC NULLS LAST
            LIMIT 200
        """)
    )
    rows = result.fetchall()

    bottlenecks = []
    for row in rows:
        bottlenecks.append({
            "clearance_id": str(row[0]),
            "project_id": str(row[1]),
            "address": row[2],
            "pathway": str(row[3]) if row[3] else None,
            "department": str(row[4]),
            "clearance_type": row[5],
            "status": str(row[6]),
            "predicted_days": row[7],
            "submitted_date": row[8].isoformat() if row[8] else None,
        })

    return bottlenecks


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

    # Use raw SQL to avoid enum casting issues
    dept_filter = ""
    params = {}
    if department:
        dept_filter = "AND c.department = :dept"
        params["dept"] = department

    result = await db.execute(
        text(f"""
            SELECT c.id, c.project_id, p.address, c.department, c.clearance_type,
                   c.status, c.is_bottleneck, c.predicted_days, c.assigned_to,
                   c.submitted_date, c.created_at
            FROM clearances c
            JOIN projects p ON c.project_id = p.id
            WHERE p.status NOT IN ('closed', 'final')
            {dept_filter}
            ORDER BY c.created_at
            LIMIT 1000
        """),
        params,
    )
    rows = result.fetchall()

    columns = {
        "not_started": [],
        "in_review": [],
        "approved": [],
        "conditional": [],
        "denied": [],
    }

    for row in rows:
        status_key = str(row[5])
        if status_key in columns:
            columns[status_key].append({
                "clearance_id": str(row[0]),
                "project_id": str(row[1]),
                "address": row[2],
                "department": str(row[3]),
                "clearance_type": row[4],
                "is_bottleneck": row[6],
                "predicted_days": row[7],
                "assigned_to": row[8],
                "submitted_date": row[9].isoformat() if row[9] else None,
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

    # Use raw SQL to avoid enum casting issues
    conditions = []
    params: dict = {"limit": size, "offset": (page - 1) * size}

    if status:
        conditions.append("status = :status")
        params["status"] = status
    if pathway:
        conditions.append("pathway = :pathway")
        params["pathway"] = pathway

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM projects {where_clause}"), params
    )).scalar() or 0

    result = await db.execute(
        text(f"""
            SELECT id, address, apn, pathway, status, predicted_days_to_issue,
                   created_at, is_coastal_zone, is_hillside
            FROM projects
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.fetchall()

    return {
        "items": [
            {
                "id": str(r[0]),
                "address": r[1],
                "apn": r[2],
                "pathway": str(r[3]) if r[3] else "standard",
                "status": str(r[4]) if r[4] else "intake",
                "predicted_days": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "is_coastal": r[7],
                "is_hillside": r[8],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }
