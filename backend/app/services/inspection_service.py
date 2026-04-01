"""Inspection scheduling and forecasting service."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inspection import Inspection
from app.models.project import Project
from app.schemas.common import InspectionStatus

logger = structlog.get_logger()

INSPECTION_SEQUENCE = [
    "Foundation",
    "Framing",
    "Rough Electrical",
    "Rough Plumbing",
    "Rough Mechanical",
    "Insulation",
    "Drywall",
    "Final Electrical",
    "Final Plumbing",
    "Final Mechanical",
    "Final Building",
]

TYPICAL_DAYS_BETWEEN_INSPECTIONS = {
    "Foundation": 7,
    "Framing": 21,
    "Rough Electrical": 3,
    "Rough Plumbing": 3,
    "Rough Mechanical": 3,
    "Insulation": 5,
    "Drywall": 7,
    "Final Electrical": 5,
    "Final Plumbing": 5,
    "Final Mechanical": 5,
    "Final Building": 7,
}


async def schedule_inspection(
    db: AsyncSession,
    project_id: UUID,
    inspection_type: str,
    scheduled_date: datetime,
    inspector_name: str | None = None,
    inspector_id: str | None = None,
    notes: str | None = None,
) -> Inspection:
    """Create a new inspection record for a project.

    Verifies the project exists before creating the inspection.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    inspection = Inspection(
        project_id=project_id,
        inspection_type=inspection_type,
        status=InspectionStatus.SCHEDULED,
        scheduled_date=scheduled_date,
        inspector_name=inspector_name,
        inspector_id=inspector_id,
        notes=notes,
    )
    db.add(inspection)
    await db.flush()
    await db.refresh(inspection)

    logger.info(
        "inspection_scheduled",
        inspection_id=str(inspection.id),
        project_id=str(project_id),
        inspection_type=inspection_type,
        scheduled_date=scheduled_date.isoformat(),
    )
    return inspection


async def get_inspections_for_project(
    db: AsyncSession,
    project_id: UUID,
) -> list[Inspection]:
    """Return all inspections for a project ordered by scheduled date."""
    stmt = (
        select(Inspection)
        .where(Inspection.project_id == project_id)
        .order_by(Inspection.scheduled_date)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_inspection_result(
    db: AsyncSession,
    inspection_id: UUID,
    status: InspectionStatus,
    failure_reasons: list[str] | None = None,
    notes: str | None = None,
) -> Inspection:
    """Update the result of an inspection.

    Sets completed_date to now when status is COMPLETED_PASS.
    """
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if inspection is None:
        raise ValueError(f"Inspection {inspection_id} not found")

    inspection.status = status

    if status in (InspectionStatus.COMPLETED_PASS, InspectionStatus.COMPLETED_FAIL):
        inspection.completed_date = datetime.now(timezone.utc)

    if failure_reasons is not None:
        inspection.failure_reasons = failure_reasons

    if notes is not None:
        inspection.notes = notes

    await db.flush()
    await db.refresh(inspection)

    logger.info(
        "inspection_result_updated",
        inspection_id=str(inspection_id),
        status=status,
    )
    return inspection


async def forecast_inspection_schedule(
    db: AsyncSession,
    project_id: UUID,
) -> dict:
    """Forecast the remaining inspection schedule for a project.

    Attempts to use Prophet for time-series forecasting if available and
    there are at least 3 historical data points. Falls back to a linear
    estimate using TYPICAL_DAYS_BETWEEN_INSPECTIONS otherwise.
    """
    inspections = await get_inspections_for_project(db, project_id)

    # Determine which inspection types have been completed (passed)
    completed_types: set[str] = {
        insp.inspection_type
        for insp in inspections
        if insp.status == InspectionStatus.COMPLETED_PASS
    }
    inspections_completed = len(completed_types)

    # Remaining types in canonical sequence order
    remaining_types = [t for t in INSPECTION_SEQUENCE if t not in completed_types]

    today = datetime.now(timezone.utc)

    # --- Attempt Prophet forecast ---
    prophet_result = None
    try:
        from prophet import Prophet  # type: ignore
        import pandas as pd  # type: ignore

        # Build a time series from completed inspections that have a scheduled_date
        completed_with_dates = sorted(
            [
                insp
                for insp in inspections
                if insp.status == InspectionStatus.COMPLETED_PASS
                and insp.scheduled_date is not None
            ],
            key=lambda i: i.scheduled_date,
        )

        if len(completed_with_dates) >= 3:
            dates = [insp.scheduled_date for insp in completed_with_dates]
            # Compute days between consecutive inspections
            intervals = [
                (dates[i] - dates[i - 1]).days for i in range(1, len(dates))
            ]
            ds_series = [dates[i] for i in range(1, len(dates))]

            df = pd.DataFrame({"ds": ds_series, "y": intervals})
            df["ds"] = pd.to_datetime(df["ds"], utc=True).dt.tz_localize(None)

            model = Prophet(daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False)
            model.fit(df)

            # Predict one step per remaining inspection
            last_date = dates[-1].replace(tzinfo=None) if dates[-1].tzinfo else dates[-1]
            future_dates = []
            cursor = last_date
            for _ in remaining_types:
                cursor = cursor + timedelta(days=7)  # nominal spacing for prophet input
                future_dates.append(cursor)

            future_df = pd.DataFrame({"ds": future_dates})
            forecast = model.predict(future_df)
            predicted_intervals = forecast["yhat"].tolist()

            remaining_list = []
            cursor_tz = datetime(last_date.year, last_date.month, last_date.day, tzinfo=timezone.utc)
            for i, insp_type in enumerate(remaining_types):
                gap = max(1, int(round(predicted_intervals[i])))
                cursor_tz = cursor_tz + timedelta(days=gap)
                days_from_now = (cursor_tz - today).days
                remaining_list.append(
                    {
                        "type": insp_type,
                        "estimated_date": cursor_tz.date().isoformat(),
                        "days_from_now": days_from_now,
                    }
                )

            estimated_final_date = remaining_list[-1]["estimated_date"] if remaining_list else today.date().isoformat()

            # Determine on_track: compare estimated final date to a naive linear baseline
            linear_days = sum(TYPICAL_DAYS_BETWEEN_INSPECTIONS.get(t, 7) for t in remaining_types)
            baseline_final = today + timedelta(days=linear_days)
            estimated_final_dt = datetime.fromisoformat(estimated_final_date)
            on_track = estimated_final_dt.date() <= baseline_final.date()

            prophet_result = {
                "inspections_completed": inspections_completed,
                "inspections_remaining": remaining_list,
                "estimated_final_date": estimated_final_date,
                "on_track": on_track,
                "method": "prophet",
            }
    except Exception:
        # Prophet not available or insufficient data — fall through to linear
        prophet_result = None

    if prophet_result is not None:
        return prophet_result

    # --- Linear forecast ---
    remaining_list = []
    cursor = today
    for insp_type in remaining_types:
        gap = TYPICAL_DAYS_BETWEEN_INSPECTIONS.get(insp_type, 7)
        cursor = cursor + timedelta(days=gap)
        days_from_now = (cursor - today).days
        remaining_list.append(
            {
                "type": insp_type,
                "estimated_date": cursor.date().isoformat(),
                "days_from_now": days_from_now,
            }
        )

    estimated_final_date = remaining_list[-1]["estimated_date"] if remaining_list else today.date().isoformat()

    # on_track: True when ahead of or equal to typical schedule
    # With linear forecast we are always exactly on the typical schedule
    on_track = True

    return {
        "inspections_completed": inspections_completed,
        "inspections_remaining": remaining_list,
        "estimated_final_date": estimated_final_date,
        "on_track": on_track,
        "method": "linear",
    }


async def get_inspection_stats(db: AsyncSession) -> dict:
    """Return aggregate inspection statistics for the staff analytics dashboard."""

    # Total inspections by status
    status_counts_result = await db.execute(
        select(Inspection.status, func.count(Inspection.id).label("cnt")).group_by(Inspection.status)
    )
    status_counts: dict[str, int] = {row.status: row.cnt for row in status_counts_result}

    total_scheduled = sum(status_counts.values())
    total_passed = status_counts.get(InspectionStatus.COMPLETED_PASS, 0)
    total_failed = status_counts.get(InspectionStatus.COMPLETED_FAIL, 0)
    total_completed = total_passed + total_failed
    pass_rate = (total_passed / total_completed) if total_completed > 0 else 0.0

    # Average days between scheduled_date and completed_date for passed inspections
    passed_result = await db.execute(
        select(Inspection.scheduled_date, Inspection.completed_date)
        .where(
            Inspection.status == InspectionStatus.COMPLETED_PASS,
            Inspection.scheduled_date.is_not(None),
            Inspection.completed_date.is_not(None),
        )
    )
    passed_rows = passed_result.all()
    if passed_rows:
        total_days = sum(
            abs((row.completed_date - row.scheduled_date).days) for row in passed_rows
        )
        avg_days_between = total_days / len(passed_rows)
    else:
        avg_days_between = 0.0

    # Most common failure reasons (flatten the ARRAY column)
    failed_result = await db.execute(
        select(Inspection.failure_reasons)
        .where(
            Inspection.status == InspectionStatus.COMPLETED_FAIL,
            Inspection.failure_reasons.is_not(None),
        )
    )
    reason_counts: dict[str, int] = {}
    for (reasons,) in failed_result:
        if reasons:
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    top_failure_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    logger.info("inspection_stats_queried")

    return {
        "total_scheduled": total_scheduled,
        "by_status": status_counts,
        "pass_rate": round(pass_rate, 4),
        "total_completed": total_completed,
        "avg_days_between_inspections": round(avg_days_between, 1),
        "top_failure_reasons": [
            {"reason": reason, "count": count} for reason, count in top_failure_reasons
        ],
    }
