"""Compliance API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.project import Project
from app.services.compliance_service import (
    full_compliance_check,
    get_pathway_requirements,
    validate_clearance_sequence,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/check/{project_id}")
async def run_compliance_check(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Run full compliance check for a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization: owners see only their projects, staff/admin see all
    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    report = full_compliance_check(project)
    return report.to_dict()


@router.get("/requirements/{pathway}")
async def get_requirements(
    pathway: str,
    current_user=Depends(get_current_user),
):
    """List requirements for a specific pathway."""
    reqs = get_pathway_requirements(pathway)
    if reqs is None:
        raise HTTPException(status_code=404, detail=f"Unknown pathway: {pathway}")
    return reqs


@router.post("/validate-sequence/{project_id}")
async def validate_sequence(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Validate clearance ordering for a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    seq_result = validate_clearance_sequence(project)
    return {
        "rule": seq_result.rule,
        "passed": seq_result.passed,
        "message": seq_result.message,
        "severity": seq_result.severity,
    }
