"""Clearance business-logic layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import CHANNEL_CLEARANCE_CHANGED, emit_event
from app.models.clearance import Clearance
from app.models.parcel import Parcel
from app.schemas.clearance import ClearanceCreate
from app.schemas.common import ClearanceDepartment, ClearanceStatus

logger = structlog.get_logger(__name__)

# ── Mapping: parcel flags -> required clearances ──────────────────────────────

_FLAG_CLEARANCES: list[tuple[str, ClearanceDepartment, str]] = [
    # (parcel_attribute, department, clearance_type)
    ("is_coastal_zone", ClearanceDepartment.DCP, "Coastal Development Permit"),
    ("is_hillside", ClearanceDepartment.LADBS, "Hillside Grading Review"),
    ("is_hillside", ClearanceDepartment.BOE, "Hillside Drainage Review"),
    ("is_very_high_fire_severity", ClearanceDepartment.LAFD, "Fire Hazard Zone Review"),
    ("is_historic", ClearanceDepartment.DCP, "Historic Preservation Review"),
    ("is_flood_zone", ClearanceDepartment.BOE, "Flood Zone Review"),
    ("is_geological_hazard", ClearanceDepartment.LADBS, "Geotechnical Review"),
    ("has_hpoz", ClearanceDepartment.DCP, "HPOZ Board Review"),
]

# Every project always needs these baseline clearances.
_BASELINE_CLEARANCES: list[tuple[ClearanceDepartment, str]] = [
    (ClearanceDepartment.LADBS, "Zoning Clearance"),
    (ClearanceDepartment.BOE, "Sewer Capacity Clearance"),
    (ClearanceDepartment.LADWP, "Power/Water Clearance"),
    (ClearanceDepartment.LASAN, "Sanitation Clearance"),
]


# ── Create ─────────────────────────────────────────────────────────────────────


async def create_clearance(
    session: AsyncSession,
    data: ClearanceCreate,
) -> Clearance:
    """Create a single clearance record."""
    clearance = Clearance(
        project_id=data.project_id,
        department=data.department,
        clearance_type=data.clearance_type,
        status=data.status,
    )
    session.add(clearance)
    await session.flush()
    await session.refresh(clearance)
    logger.info(
        "clearance_created",
        clearance_id=str(clearance.id),
        project_id=str(data.project_id),
        department=data.department,
    )
    return clearance


# ── Update status ──────────────────────────────────────────────────────────────


async def update_clearance_status(
    session: AsyncSession,
    clearance_id: uuid.UUID,
    status: ClearanceStatus,
    redis: aioredis.Redis | None = None,
) -> Clearance | None:
    """Update a clearance status and emit a ``clearance_changed`` event."""
    stmt = select(Clearance).where(Clearance.id == clearance_id)
    result = await session.execute(stmt)
    clearance = result.scalar_one_or_none()
    if clearance is None:
        return None

    old_status = clearance.status
    clearance.status = status

    if status in (ClearanceStatus.APPROVED, ClearanceStatus.NOT_APPLICABLE):
        clearance.completed_date = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(clearance)

    logger.info(
        "clearance_status_updated",
        clearance_id=str(clearance_id),
        old_status=old_status,
        new_status=status,
    )

    # Emit event for the notification pipeline
    if redis is not None:
        await emit_event(redis, CHANNEL_CLEARANCE_CHANGED, {
            "clearance_id": str(clearance.id),
            "project_id": str(clearance.project_id),
            "department": clearance.department,
            "clearance_type": clearance.clearance_type,
            "old_status": old_status,
            "new_status": status,
            "status": status,
        })

    return clearance


# ── Query ──────────────────────────────────────────────────────────────────────


async def get_clearances_for_project(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> list[Clearance]:
    """Return all clearances associated with *project_id*."""
    stmt = (
        select(Clearance)
        .where(Clearance.project_id == project_id)
        .order_by(Clearance.department, Clearance.clearance_type)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Auto-generation from parcel attributes ─────────────────────────────────────


async def auto_generate_clearances(
    session: AsyncSession,
    project_id: uuid.UUID,
    parcel: Parcel,
) -> list[Clearance]:
    """Generate required clearances based on parcel overlay flags.

    1. Always creates the baseline clearances (zoning, sewer, power/water,
       sanitation).
    2. Conditionally adds clearances for special zones (coastal, hillside,
       fire, historic, flood, geohazard, HPOZ) based on parcel attributes.

    Duplicate clearances (same project + department + type) are skipped.
    """
    # Gather existing clearances so we don't duplicate
    existing = await get_clearances_for_project(session, project_id)
    existing_keys: set[tuple[str, str]] = {
        (c.department, c.clearance_type) for c in existing
    }

    to_create: list[tuple[ClearanceDepartment, str]] = []

    # Baseline
    for dept, ctype in _BASELINE_CLEARANCES:
        if (dept, ctype) not in existing_keys:
            to_create.append((dept, ctype))

    # Conditional on parcel flags
    for flag_attr, dept, ctype in _FLAG_CLEARANCES:
        if getattr(parcel, flag_attr, False) and (dept, ctype) not in existing_keys:
            to_create.append((dept, ctype))

    created: list[Clearance] = []
    for dept, ctype in to_create:
        clearance = Clearance(
            project_id=project_id,
            department=dept,
            clearance_type=ctype,
            status=ClearanceStatus.NOT_STARTED,
        )
        session.add(clearance)
        created.append(clearance)

    if created:
        await session.flush()
        for c in created:
            await session.refresh(c)

    logger.info(
        "clearances_auto_generated",
        project_id=str(project_id),
        count=len(created),
        types=[c.clearance_type for c in created],
    )
    return created
