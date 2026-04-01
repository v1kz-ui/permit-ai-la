"""Report API endpoints for staff-only report generation.

Provides weekly summaries, department workload reports,
project status reports, and scheduled recurring reports.
"""

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.redis import get_redis
from app.middleware.auth import get_current_user
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _require_staff(current_user):
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Staff access required")


@router.get("/weekly")
async def get_weekly_report(
    week: date = Query(
        ...,
        description="Monday of the report week (YYYY-MM-DD)",
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Weekly summary report: new projects, clearances completed, bottlenecks resolved."""
    _require_staff(current_user)
    return await report_service.generate_weekly_report(db, week)


@router.get("/department/{department}")
async def get_department_report(
    department: str,
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Per-department workload report for a date range."""
    _require_staff(current_user)

    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    return await report_service.generate_department_report(db, department, (start, end))


@router.get("/project/{project_id}")
async def get_project_report(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Full project status report with timeline."""
    _require_staff(current_user)

    result = await report_service.generate_project_report(db, project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


class ScheduleReportRequest(BaseModel):
    report_type: str  # "weekly" | "department"
    department: str | None = None
    frequency: str = "weekly"  # "daily" | "weekly" | "monthly"
    recipients: list[str] = []  # email addresses


@router.post("/schedule")
async def schedule_report(
    request: ScheduleReportRequest,
    current_user=Depends(get_current_user),
):
    """Schedule a recurring report. Stores configuration in Redis."""
    _require_staff(current_user)

    valid_types = ("weekly", "department")
    if request.report_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report_type. Must be one of: {', '.join(valid_types)}",
        )

    if request.report_type == "department" and not request.department:
        raise HTTPException(
            status_code=400,
            detail="department is required for department reports",
        )

    valid_frequencies = ("daily", "weekly", "monthly")
    if request.frequency not in valid_frequencies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}",
        )

    redis = await get_redis()

    schedule_key = f"report_schedule:{request.report_type}:{request.department or 'all'}"
    schedule_data = {
        "report_type": request.report_type,
        "department": request.department,
        "frequency": request.frequency,
        "recipients": request.recipients,
        "created_by": str(current_user.id),
    }

    await redis.set(schedule_key, json.dumps(schedule_data))

    # Also add to the set of all scheduled reports
    await redis.sadd("report_schedules", schedule_key)

    return {
        "status": "scheduled",
        "schedule_key": schedule_key,
        "config": schedule_data,
    }
