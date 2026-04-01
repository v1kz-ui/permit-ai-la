"""Report generation service for PermitAI LA.

Generates weekly summaries, department workload reports, and
full project status reports with timelines.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clearance import Clearance
from app.models.inspection import Inspection
from app.models.project import Project


async def generate_weekly_report(
    db: AsyncSession,
    week_start: date,
) -> dict:
    """Creates weekly summary: new projects, clearances completed,
    bottlenecks resolved, avg processing time.

    Args:
        db: Async database session.
        week_start: Monday of the report week.

    Returns:
        Dict with weekly summary data.
    """
    week_end = week_start + timedelta(days=7)
    start_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
    end_dt = datetime(week_end.year, week_end.month, week_end.day, tzinfo=timezone.utc)

    # New projects this week
    new_projects_count = (await db.execute(
        select(func.count(Project.id)).where(
            Project.created_at >= start_dt,
            Project.created_at < end_dt,
        )
    )).scalar() or 0

    # Projects issued this week
    issued_count = (await db.execute(
        select(func.count(Project.id)).where(
            Project.issued_date >= start_dt,
            Project.issued_date < end_dt,
        )
    )).scalar() or 0

    # Clearances completed this week
    clearances_completed = (await db.execute(
        select(func.count(Clearance.id)).where(
            Clearance.completed_date >= start_dt,
            Clearance.completed_date < end_dt,
        )
    )).scalar() or 0

    # Clearances completed by department this week
    dept_completions = (await db.execute(
        select(
            Clearance.department,
            func.count(Clearance.id).label("completed"),
        )
        .where(
            Clearance.completed_date >= start_dt,
            Clearance.completed_date < end_dt,
        )
        .group_by(Clearance.department)
        .order_by(func.count(Clearance.id).desc())
    )).all()

    # Bottlenecks active at end of week
    active_bottlenecks = (await db.execute(
        select(func.count(Clearance.id)).where(
            Clearance.is_bottleneck.is_(True),
            Clearance.status.in_(["not_started", "in_review"]),
        )
    )).scalar() or 0

    # Bottlenecks resolved this week (completed clearances that were flagged)
    bottlenecks_resolved = (await db.execute(
        select(func.count(Clearance.id)).where(
            Clearance.is_bottleneck.is_(True),
            Clearance.completed_date >= start_dt,
            Clearance.completed_date < end_dt,
        )
    )).scalar() or 0

    # Avg processing time for clearances completed this week
    avg_processing = (await db.execute(
        select(
            func.avg(
                extract("epoch", Clearance.completed_date - Clearance.submitted_date) / 86400
            )
        ).where(
            Clearance.completed_date >= start_dt,
            Clearance.completed_date < end_dt,
            Clearance.submitted_date.isnot(None),
        )
    )).scalar()

    # Projects by status snapshot
    status_snapshot = (await db.execute(
        select(Project.status, func.count(Project.id))
        .group_by(Project.status)
    )).all()

    return {
        "report_type": "weekly",
        "week_start": week_start.isoformat(),
        "week_end": (week_end - timedelta(days=1)).isoformat(),
        "new_projects": new_projects_count,
        "permits_issued": issued_count,
        "clearances_completed": clearances_completed,
        "department_completions": [
            {"department": str(dept), "completed": count}
            for dept, count in dept_completions
        ],
        "active_bottlenecks": active_bottlenecks,
        "bottlenecks_resolved": bottlenecks_resolved,
        "avg_processing_days": round(float(avg_processing), 1) if avg_processing else None,
        "status_snapshot": {str(s): c for s, c in status_snapshot},
    }


async def generate_department_report(
    db: AsyncSession,
    department: str,
    date_range: tuple[date, date],
) -> dict:
    """Per-department workload report.

    Args:
        db: Async database session.
        department: Department enum value string.
        date_range: (start_date, end_date) for the report period.

    Returns:
        Dict with department workload breakdown.
    """
    start, end = date_range
    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)

    # Total clearances in department during period
    total = (await db.execute(
        select(func.count(Clearance.id)).where(
            Clearance.department == department,
            Clearance.created_at >= start_dt,
            Clearance.created_at <= end_dt,
        )
    )).scalar() or 0

    # Status breakdown
    status_breakdown = (await db.execute(
        select(Clearance.status, func.count(Clearance.id))
        .where(
            Clearance.department == department,
            Clearance.created_at >= start_dt,
            Clearance.created_at <= end_dt,
        )
        .group_by(Clearance.status)
    )).all()

    # Avg processing time
    avg_days = (await db.execute(
        select(
            func.avg(
                extract("epoch", Clearance.completed_date - Clearance.submitted_date) / 86400
            )
        ).where(
            Clearance.department == department,
            Clearance.completed_date >= start_dt,
            Clearance.completed_date <= end_dt,
            Clearance.submitted_date.isnot(None),
        )
    )).scalar()

    # Workload by clearance type
    by_type = (await db.execute(
        select(
            Clearance.clearance_type,
            func.count(Clearance.id).label("count"),
            func.avg(
                case(
                    (
                        Clearance.completed_date.isnot(None),
                        extract("epoch", Clearance.completed_date - Clearance.submitted_date) / 86400,
                    ),
                    else_=None,
                )
            ).label("avg_days"),
        )
        .where(
            Clearance.department == department,
            Clearance.created_at >= start_dt,
            Clearance.created_at <= end_dt,
        )
        .group_by(Clearance.clearance_type)
        .order_by(func.count(Clearance.id).desc())
    )).all()

    # Bottleneck count
    bottleneck_count = (await db.execute(
        select(func.count(Clearance.id)).where(
            Clearance.department == department,
            Clearance.is_bottleneck.is_(True),
            Clearance.created_at >= start_dt,
            Clearance.created_at <= end_dt,
        )
    )).scalar() or 0

    # Assigned-to distribution
    assignee_workload = (await db.execute(
        select(
            Clearance.assigned_to,
            func.count(Clearance.id).label("count"),
        )
        .where(
            Clearance.department == department,
            Clearance.assigned_to.isnot(None),
            Clearance.created_at >= start_dt,
            Clearance.created_at <= end_dt,
        )
        .group_by(Clearance.assigned_to)
        .order_by(func.count(Clearance.id).desc())
    )).all()

    return {
        "report_type": "department",
        "department": department,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_clearances": total,
        "status_breakdown": {str(s): c for s, c in status_breakdown},
        "avg_processing_days": round(float(avg_days), 1) if avg_days else None,
        "by_clearance_type": [
            {
                "clearance_type": ct,
                "count": count,
                "avg_days": round(float(avg), 1) if avg else None,
            }
            for ct, count, avg in by_type
        ],
        "bottleneck_count": bottleneck_count,
        "assignee_workload": [
            {"assigned_to": name, "count": count}
            for name, count in assignee_workload
        ],
    }


async def generate_project_report(
    db: AsyncSession,
    project_id: str,
) -> dict:
    """Full project status report with timeline.

    Args:
        db: Async database session.
        project_id: UUID string of the project.

    Returns:
        Dict with complete project status, clearances, inspections, and timeline.
    """
    # Get project
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        return {"error": "Project not found", "project_id": project_id}

    # Get all clearances for project
    clearances_result = await db.execute(
        select(Clearance)
        .where(Clearance.project_id == project_id)
        .order_by(Clearance.department)
    )
    clearances = clearances_result.scalars().all()

    # Get all inspections for project
    inspections_result = await db.execute(
        select(Inspection)
        .where(Inspection.project_id == project_id)
        .order_by(Inspection.scheduled_date)
    )
    inspections = inspections_result.scalars().all()

    # Build timeline events
    timeline = []

    if project.application_date:
        timeline.append({
            "event": "Application submitted",
            "date": project.application_date.isoformat(),
            "type": "milestone",
        })

    if project.created_at:
        timeline.append({
            "event": "Project created in system",
            "date": project.created_at.isoformat(),
            "type": "system",
        })

    for c in clearances:
        if c.submitted_date:
            timeline.append({
                "event": f"{c.department} - {c.clearance_type} submitted",
                "date": c.submitted_date.isoformat(),
                "type": "clearance_submitted",
            })
        if c.completed_date:
            timeline.append({
                "event": f"{c.department} - {c.clearance_type} {c.status}",
                "date": c.completed_date.isoformat(),
                "type": f"clearance_{c.status}",
            })

    for insp in inspections:
        if insp.scheduled_date:
            timeline.append({
                "event": f"Inspection: {insp.inspection_type} ({insp.status})",
                "date": insp.scheduled_date.isoformat(),
                "type": "inspection",
            })

    if project.issued_date:
        timeline.append({
            "event": "Permit issued",
            "date": project.issued_date.isoformat(),
            "type": "milestone",
        })

    timeline.sort(key=lambda x: x["date"])

    # Clearance summary
    clearance_summary = {
        "total": len(clearances),
        "completed": sum(1 for c in clearances if c.status in ("approved", "conditional", "not_applicable")),
        "pending": sum(1 for c in clearances if c.status in ("not_started", "in_review")),
        "denied": sum(1 for c in clearances if c.status == "denied"),
        "bottlenecks": sum(1 for c in clearances if c.is_bottleneck),
    }

    return {
        "report_type": "project",
        "project": {
            "id": str(project.id),
            "address": project.address,
            "apn": project.apn,
            "pathway": str(project.pathway),
            "status": str(project.status),
            "description": project.description,
            "application_date": project.application_date.isoformat() if project.application_date else None,
            "issued_date": project.issued_date.isoformat() if project.issued_date else None,
            "predicted_days_to_issue": project.predicted_days_to_issue,
            "is_coastal_zone": project.is_coastal_zone,
            "is_hillside": project.is_hillside,
            "is_very_high_fire_severity": project.is_very_high_fire_severity,
            "is_historic": project.is_historic,
        },
        "clearance_summary": clearance_summary,
        "clearances": [
            {
                "id": str(c.id),
                "department": str(c.department),
                "clearance_type": c.clearance_type,
                "status": str(c.status),
                "is_bottleneck": c.is_bottleneck,
                "assigned_to": c.assigned_to,
                "submitted_date": c.submitted_date.isoformat() if c.submitted_date else None,
                "completed_date": c.completed_date.isoformat() if c.completed_date else None,
                "predicted_days": c.predicted_days,
                "notes": c.notes,
            }
            for c in clearances
        ],
        "inspections": [
            {
                "id": str(insp.id),
                "inspection_type": insp.inspection_type,
                "status": str(insp.status),
                "scheduled_date": insp.scheduled_date.isoformat() if insp.scheduled_date else None,
                "completed_date": insp.completed_date.isoformat() if insp.completed_date else None,
                "inspector_name": insp.inspector_name,
                "notes": insp.notes,
            }
            for insp in inspections
        ],
        "timeline": timeline,
    }
