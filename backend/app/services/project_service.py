"""Project business-logic layer."""

from __future__ import annotations

import math
import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parcel import Parcel
from app.models.project import Project
from app.schemas.common import PaginatedResponse, ProjectPathway, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = structlog.get_logger(__name__)


# ── Create ─────────────────────────────────────────────────────────────────────


async def create_project(
    session: AsyncSession,
    owner_id: uuid.UUID,
    data: ProjectCreate,
) -> Project:
    """Create a new project, look up the parcel by address and auto-set flags."""
    parcel = await _lookup_parcel_by_address(session, data.address)

    project = Project(
        owner_id=owner_id,
        address=data.address,
        description=data.description,
        original_sqft=data.original_sqft,
        proposed_sqft=data.proposed_sqft,
        stories=data.stories,
        pathway=ProjectPathway.UNKNOWN,
        status=ProjectStatus.INTAKE,
    )

    if parcel is not None:
        project.apn = parcel.apn
        project.is_coastal_zone = parcel.is_coastal_zone
        project.is_hillside = parcel.is_hillside
        project.is_very_high_fire_severity = parcel.is_very_high_fire_severity
        project.is_historic = parcel.is_historic
        logger.info(
            "parcel_linked",
            apn=parcel.apn,
            address=data.address,
            coastal=parcel.is_coastal_zone,
            hillside=parcel.is_hillside,
            fire=parcel.is_very_high_fire_severity,
            historic=parcel.is_historic,
        )
    else:
        logger.warning("parcel_not_found", address=data.address)

    session.add(project)
    await session.flush()
    await session.refresh(project)
    logger.info("project_created", project_id=str(project.id), address=data.address)
    return project


# ── Read ───────────────────────────────────────────────────────────────────────


async def get_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Project | None:
    """Get a single project with authorisation check (owner must match)."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.owner_id == owner_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── List ───────────────────────────────────────────────────────────────────────


async def list_projects(
    session: AsyncSession,
    owner_id: uuid.UUID,
    status: ProjectStatus | None = None,
    pathway: ProjectPathway | None = None,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse:
    """Return a paginated, filtered list of projects for *owner_id*."""
    base = select(Project).where(Project.owner_id == owner_id)

    if status is not None:
        base = base.where(Project.status == status)
    if pathway is not None:
        base = base.where(Project.pathway == pathway)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Paginated rows
    offset = (page - 1) * size
    rows_stmt = base.order_by(Project.created_at.desc()).offset(offset).limit(size)
    result = await session.execute(rows_stmt)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


# ── Update ─────────────────────────────────────────────────────────────────────


async def update_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: ProjectUpdate,
) -> Project | None:
    """Partial update of a project (only non-None fields are applied)."""
    project = await get_project(session, project_id, owner_id)
    if project is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await session.flush()
    await session.refresh(project)
    logger.info(
        "project_updated",
        project_id=str(project.id),
        fields=list(update_data.keys()),
    )
    return project


# ── Internal helpers ───────────────────────────────────────────────────────────


async def _lookup_parcel_by_address(
    session: AsyncSession,
    address: str,
) -> Parcel | None:
    """Try to find a parcel whose address matches (case-insensitive)."""
    stmt = select(Parcel).where(
        func.lower(Parcel.address) == func.lower(address.strip())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
