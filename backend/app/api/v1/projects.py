from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.clearance import Clearance
from app.models.parcel import Parcel
from app.models.project import Project
from app.schemas.common import ProjectPathway, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectDetailResponse, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    if len(data.address.strip()) > 500:
        raise HTTPException(status_code=400, detail="Address too long (max 500 characters)")

    # Try to find matching parcel by address
    parcel = None
    normalized_addr = data.address.upper().strip()
    result = await db.execute(
        select(Parcel).where(func.upper(Parcel.address).like(f"%{normalized_addr}%")).limit(1)
    )
    parcel = result.scalar_one_or_none()

    project = Project(
        address=data.address,
        owner_id=current_user.id,
        description=data.description,
        original_sqft=data.original_sqft,
        proposed_sqft=data.proposed_sqft,
        stories=data.stories,
        pathway=ProjectPathway.UNKNOWN,
        status=ProjectStatus.INTAKE,
    )

    # Link parcel data if found
    if parcel:
        project.apn = parcel.apn
        project.is_coastal_zone = parcel.is_coastal_zone
        project.is_hillside = parcel.is_hillside
        project.is_very_high_fire_severity = parcel.is_very_high_fire_severity
        project.is_historic = parcel.is_historic

    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization: owners see only their projects, staff/admin see all
    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    status: ProjectStatus | None = None,
    pathway: ProjectPathway | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    query = select(Project)

    # Authorization: homeowners see only their projects
    if current_user.role not in ("staff", "admin"):
        query = query.where(Project.owner_id == current_user.id)

    if status:
        query = query.where(Project.status == status)
    if pathway:
        query = query.where(Project.pathway == pathway)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * size).limit(size).order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    return projects


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    return project
