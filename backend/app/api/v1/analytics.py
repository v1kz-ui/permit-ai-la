"""Analytics API endpoints for staff-only pipeline analytics.

Provides pipeline metrics, geographic heatmap data, department performance,
time-series trends, equity metrics, and data export.
"""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _require_staff(current_user):
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Staff access required")


def _safe_csv(value: object) -> str:
    """Escape CSV values to prevent formula injection in Excel/Sheets."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


@router.get("/pipeline")
async def get_pipeline_metrics(
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Pipeline metrics: completion rates, avg days, bottleneck frequency by department."""
    _require_staff(current_user)

    date_range = None
    if start_date and end_date:
        date_range = (start_date, end_date)

    return await analytics_service.get_pipeline_metrics(db, date_range)


@router.get("/geographic")
async def get_geographic_heatmap(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Geographic heatmap data: lat/lng clusters of active projects with status counts."""
    _require_staff(current_user)
    return await analytics_service.get_geographic_heatmap_data(db)


@router.get("/department/{department}")
async def get_department_performance(
    department: str,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Historical department performance: avg processing days, approval rate, rejection reasons."""
    _require_staff(current_user)
    return await analytics_service.get_department_performance(db, department)


@router.get("/trends")
async def get_trends(
    metric: str = Query(
        ...,
        description="Metric to trend: permits_issued, clearances_completed, bottlenecks_detected",
    ),
    period: str = Query(
        "day",
        description="Grouping period: day, week, month",
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Time-series trend data for a given metric grouped by period."""
    _require_staff(current_user)

    valid_metrics = ("permits_issued", "clearances_completed", "bottlenecks_detected")
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
        )

    valid_periods = ("day", "week", "month")
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    return await analytics_service.get_trend_data(db, metric, period)


@router.get("/equity")
async def get_equity_metrics(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Equity metrics: processing time by area, language distribution, pathway distribution."""
    _require_staff(current_user)
    return await analytics_service.get_equity_metrics(db)


@router.get("/export")
async def export_analytics(
    format: str = Query("json", description="Export format: csv or json"),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Export analytics data as CSV or JSON."""
    _require_staff(current_user)

    pipeline = await analytics_service.get_pipeline_metrics(db)
    equity = await analytics_service.get_equity_metrics(db)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Pipeline metrics header
        writer.writerow([_safe_csv("Department Analytics")])
        writer.writerow([
            _safe_csv("Department"), _safe_csv("Total"), _safe_csv("Completed"),
            _safe_csv("Completion Rate (%)"), _safe_csv("Avg Processing Days"),
            _safe_csv("Bottleneck Count"),
        ])
        for dept in pipeline.get("departments", []):
            writer.writerow([
                _safe_csv(dept["department"]),
                _safe_csv(dept["total"]),
                _safe_csv(dept["completed"]),
                _safe_csv(dept["completion_rate"]),
                _safe_csv(dept["avg_processing_days"] or "N/A"),
                _safe_csv(dept["bottleneck_count"]),
            ])

        writer.writerow([])
        writer.writerow([_safe_csv("Equity Metrics - By Area")])
        writer.writerow([
            _safe_csv("Area"), _safe_csv("Project Count"),
            _safe_csv("Avg Predicted Days"), _safe_csv("Avg Actual Days"),
        ])
        for area in equity.get("areas", []):
            writer.writerow([
                _safe_csv(area["area"]),
                _safe_csv(area["project_count"]),
                _safe_csv(area["avg_predicted_days"] or "N/A"),
                _safe_csv(area["avg_actual_days"] or "N/A"),
            ])

        writer.writerow([])
        writer.writerow([_safe_csv("Language Distribution")])
        writer.writerow([_safe_csv("Language"), _safe_csv("Count")])
        for lang in equity.get("languages", []):
            writer.writerow([_safe_csv(lang["language"]), _safe_csv(lang["count"])])

        writer.writerow([])
        writer.writerow([_safe_csv("Pathway Distribution")])
        writer.writerow([_safe_csv("Pathway"), _safe_csv("Count"), _safe_csv("Avg Predicted Days")])
        for pw in equity.get("pathways", []):
            writer.writerow([
                _safe_csv(pw["pathway"]),
                _safe_csv(pw["count"]),
                _safe_csv(pw["avg_predicted_days"] or "N/A"),
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
        )

    # Default: JSON
    return {
        "pipeline": pipeline,
        "equity": equity,
    }
