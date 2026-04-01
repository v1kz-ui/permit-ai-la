"""Analytics service for PermitAI LA pipeline metrics and reporting.

Provides aggregated analytics data including pipeline throughput,
geographic heatmaps, department performance, time-series trends,
and equity metrics across fire-rebuild permit areas.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clearance import Clearance
from app.models.parcel import Parcel
from app.models.project import Project
from app.models.user import User


async def get_pipeline_metrics(
    db: AsyncSession,
    date_range: tuple[date, date] | None = None,
) -> dict:
    """Clearance completion rates by department, avg days, bottleneck frequency.

    Args:
        db: Async database session.
        date_range: Optional (start_date, end_date) filter.

    Returns:
        Dict with department-level completion rates, avg processing days,
        and bottleneck frequency counts.
    """
    base_filter = []
    if date_range:
        start, end = date_range
        base_filter.append(Clearance.created_at >= datetime(start.year, start.month, start.day, tzinfo=timezone.utc))
        base_filter.append(Clearance.created_at <= datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc))

    # Completion rates by department
    completion_query = (
        select(
            Clearance.department,
            func.count(Clearance.id).label("total"),
            func.count(
                case(
                    (Clearance.status.in_(["approved", "conditional", "not_applicable"]), Clearance.id),
                    else_=None,
                )
            ).label("completed"),
            func.avg(
                case(
                    (
                        Clearance.completed_date.isnot(None),
                        extract("epoch", Clearance.completed_date - Clearance.submitted_date) / 86400,
                    ),
                    else_=None,
                )
            ).label("avg_days"),
            func.count(
                case(
                    (Clearance.is_bottleneck.is_(True), Clearance.id),
                    else_=None,
                )
            ).label("bottleneck_count"),
        )
        .where(*base_filter)
        .group_by(Clearance.department)
    )

    result = await db.execute(completion_query)
    rows = result.all()

    departments = []
    total_clearances = 0
    total_completed = 0
    total_bottlenecks = 0

    for dept, total, completed, avg_days, bottleneck_count in rows:
        total_clearances += total
        total_completed += completed
        total_bottlenecks += bottleneck_count
        departments.append({
            "department": str(dept),
            "total": total,
            "completed": completed,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0.0,
            "avg_processing_days": round(float(avg_days), 1) if avg_days else None,
            "bottleneck_count": bottleneck_count,
        })

    return {
        "departments": departments,
        "summary": {
            "total_clearances": total_clearances,
            "total_completed": total_completed,
            "overall_completion_rate": round(total_completed / total_clearances * 100, 1) if total_clearances > 0 else 0.0,
            "total_bottlenecks": total_bottlenecks,
        },
    }


async def get_geographic_heatmap_data(db: AsyncSession) -> dict:
    """PostGIS query returning lat/lng clusters of active projects with status counts.

    Returns:
        Dict with clustered geographic data points including project counts
        and status breakdowns.
    """
    query = (
        select(
            func.ST_X(func.ST_Centroid(Parcel.geom)).label("lng"),
            func.ST_Y(func.ST_Centroid(Parcel.geom)).label("lat"),
            Project.status,
            func.count(Project.id).label("count"),
            Parcel.community_plan_area,
        )
        .join(Parcel, Project.apn == Parcel.apn)
        .where(Parcel.geom.isnot(None))
        .where(Project.status.notin_(["closed", "final"]))
        .group_by(
            func.ST_X(func.ST_Centroid(Parcel.geom)),
            func.ST_Y(func.ST_Centroid(Parcel.geom)),
            Project.status,
            Parcel.community_plan_area,
        )
    )

    result = await db.execute(query)
    rows = result.all()

    points = []
    for lng, lat, status, count, area in rows:
        if lat is not None and lng is not None:
            points.append({
                "lat": float(lat),
                "lng": float(lng),
                "status": str(status),
                "count": count,
                "community_plan_area": area,
            })

    return {"points": points, "total": len(points)}


async def get_department_performance(
    db: AsyncSession,
    department: str,
) -> dict:
    """Historical performance for a department: avg processing days,
    approval rate, rejection reasons.

    Args:
        db: Async database session.
        department: Department enum value string.

    Returns:
        Dict with avg processing days, approval/denial rates, and
        top rejection reasons.
    """
    base_query = select(Clearance).where(Clearance.department == department)

    # Aggregate stats
    stats_query = (
        select(
            func.count(Clearance.id).label("total"),
            func.count(
                case((Clearance.status == "approved", Clearance.id), else_=None)
            ).label("approved"),
            func.count(
                case((Clearance.status == "conditional", Clearance.id), else_=None)
            ).label("conditional"),
            func.count(
                case((Clearance.status == "denied", Clearance.id), else_=None)
            ).label("denied"),
            func.count(
                case((Clearance.status == "in_review", Clearance.id), else_=None)
            ).label("in_review"),
            func.avg(
                case(
                    (
                        Clearance.completed_date.isnot(None),
                        extract("epoch", Clearance.completed_date - Clearance.submitted_date) / 86400,
                    ),
                    else_=None,
                )
            ).label("avg_days"),
            func.count(
                case((Clearance.is_bottleneck.is_(True), Clearance.id), else_=None)
            ).label("bottleneck_count"),
        )
        .where(Clearance.department == department)
    )

    result = await db.execute(stats_query)
    row = result.one()
    total, approved, conditional, denied, in_review, avg_days, bottleneck_count = row

    # Monthly trend (last 12 months)
    monthly_query = (
        select(
            func.date_trunc("month", Clearance.created_at).label("month"),
            func.count(Clearance.id).label("total"),
            func.count(
                case((Clearance.status == "approved", Clearance.id), else_=None)
            ).label("approved"),
        )
        .where(Clearance.department == department)
        .where(Clearance.created_at >= func.now() - text("interval '12 months'"))
        .group_by(func.date_trunc("month", Clearance.created_at))
        .order_by(func.date_trunc("month", Clearance.created_at))
    )

    monthly_result = await db.execute(monthly_query)
    monthly_rows = monthly_result.all()

    monthly_trend = [
        {
            "month": m.isoformat() if m else None,
            "total": t,
            "approved": a,
        }
        for m, t, a in monthly_rows
    ]

    # Top denial/conditional notes
    denial_query = (
        select(Clearance.notes, func.count(Clearance.id).label("count"))
        .where(Clearance.department == department)
        .where(Clearance.status.in_(["denied", "conditional"]))
        .where(Clearance.notes.isnot(None))
        .group_by(Clearance.notes)
        .order_by(func.count(Clearance.id).desc())
        .limit(10)
    )

    denial_result = await db.execute(denial_query)
    rejection_reasons = [
        {"reason": note, "count": count}
        for note, count in denial_result.all()
    ]

    return {
        "department": department,
        "total_clearances": total,
        "approved": approved,
        "conditional": conditional,
        "denied": denied,
        "in_review": in_review,
        "approval_rate": round((approved + conditional) / total * 100, 1) if total > 0 else 0.0,
        "avg_processing_days": round(float(avg_days), 1) if avg_days else None,
        "bottleneck_count": bottleneck_count,
        "monthly_trend": monthly_trend,
        "rejection_reasons": rejection_reasons,
    }


async def get_trend_data(
    db: AsyncSession,
    metric: str,
    period: str = "day",
) -> dict:
    """Time-series data for any metric grouped by day/week/month.

    Args:
        db: Async database session.
        metric: One of permits_issued, clearances_completed, bottlenecks_detected.
        period: Grouping period - day, week, or month.

    Returns:
        Dict with time-series data points.
    """
    trunc_period = period if period in ("day", "week", "month") else "day"

    if metric == "permits_issued":
        query = (
            select(
                func.date_trunc(trunc_period, Project.issued_date).label("period"),
                func.count(Project.id).label("value"),
            )
            .where(Project.issued_date.isnot(None))
            .group_by(func.date_trunc(trunc_period, Project.issued_date))
            .order_by(func.date_trunc(trunc_period, Project.issued_date))
        )
    elif metric == "clearances_completed":
        query = (
            select(
                func.date_trunc(trunc_period, Clearance.completed_date).label("period"),
                func.count(Clearance.id).label("value"),
            )
            .where(Clearance.completed_date.isnot(None))
            .group_by(func.date_trunc(trunc_period, Clearance.completed_date))
            .order_by(func.date_trunc(trunc_period, Clearance.completed_date))
        )
    elif metric == "bottlenecks_detected":
        query = (
            select(
                func.date_trunc(trunc_period, Clearance.created_at).label("period"),
                func.count(Clearance.id).label("value"),
            )
            .where(Clearance.is_bottleneck.is_(True))
            .group_by(func.date_trunc(trunc_period, Clearance.created_at))
            .order_by(func.date_trunc(trunc_period, Clearance.created_at))
        )
    else:
        return {"metric": metric, "period": period, "data": [], "error": "Unknown metric"}

    result = await db.execute(query)
    rows = result.all()

    data = [
        {
            "period": p.isoformat() if p else None,
            "value": v,
        }
        for p, v in rows
    ]

    return {"metric": metric, "period": period, "data": data}


async def get_equity_metrics(db: AsyncSession) -> dict:
    """Processing time by area (Palisades vs Altadena), language distribution,
    pathway distribution.

    Returns:
        Dict with area-based comparisons and demographic breakdowns.
    """
    # Processing time by community plan area (focus on fire-affected areas)
    area_query = (
        select(
            Parcel.community_plan_area,
            func.count(Project.id).label("project_count"),
            func.avg(Project.predicted_days_to_issue).label("avg_predicted_days"),
            func.avg(
                case(
                    (
                        Project.issued_date.isnot(None),
                        extract("epoch", Project.issued_date - Project.application_date) / 86400,
                    ),
                    else_=None,
                )
            ).label("avg_actual_days"),
        )
        .join(Parcel, Project.apn == Parcel.apn)
        .where(Parcel.community_plan_area.isnot(None))
        .group_by(Parcel.community_plan_area)
        .order_by(func.count(Project.id).desc())
    )

    area_result = await db.execute(area_query)
    area_rows = area_result.all()

    areas = [
        {
            "area": area,
            "project_count": count,
            "avg_predicted_days": round(float(pred), 1) if pred else None,
            "avg_actual_days": round(float(actual), 1) if actual else None,
        }
        for area, count, pred, actual in area_rows
    ]

    # Language distribution of project owners
    language_query = (
        select(
            User.language,
            func.count(Project.id).label("count"),
        )
        .join(User, Project.owner_id == User.id)
        .group_by(User.language)
        .order_by(func.count(Project.id).desc())
    )

    lang_result = await db.execute(language_query)
    languages = [
        {"language": str(lang), "count": count}
        for lang, count in lang_result.all()
    ]

    # Pathway distribution
    pathway_query = (
        select(
            Project.pathway,
            func.count(Project.id).label("count"),
            func.avg(Project.predicted_days_to_issue).label("avg_days"),
        )
        .group_by(Project.pathway)
        .order_by(func.count(Project.id).desc())
    )

    pathway_result = await db.execute(pathway_query)
    pathways = [
        {
            "pathway": str(pw),
            "count": count,
            "avg_predicted_days": round(float(avg), 1) if avg else None,
        }
        for pw, count, avg in pathway_result.all()
    ]

    # Fire-severity zone comparison
    fire_zone_query = (
        select(
            Project.is_very_high_fire_severity,
            func.count(Project.id).label("count"),
            func.avg(Project.predicted_days_to_issue).label("avg_days"),
        )
        .group_by(Project.is_very_high_fire_severity)
    )

    fire_result = await db.execute(fire_zone_query)
    fire_zone = [
        {
            "is_vhfhsz": is_fire,
            "count": count,
            "avg_predicted_days": round(float(avg), 1) if avg else None,
        }
        for is_fire, count, avg in fire_result.all()
    ]

    return {
        "areas": areas,
        "languages": languages,
        "pathways": pathways,
        "fire_zone_comparison": fire_zone,
    }
