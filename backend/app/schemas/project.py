from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.clearance import ClearanceResponse
from app.schemas.common import ProjectPathway, ProjectStatus


class ProjectCreate(BaseModel):
    address: str
    description: str | None = None
    original_sqft: float | None = None
    proposed_sqft: float | None = None
    stories: int | None = None


class ProjectUpdate(BaseModel):
    description: str | None = None
    status: ProjectStatus | None = None
    pathway: ProjectPathway | None = None
    original_sqft: float | None = None
    proposed_sqft: float | None = None
    stories: int | None = None


class ProjectResponse(BaseModel):
    id: UUID
    address: str
    apn: str | None
    owner_id: UUID
    ladbs_permit_number: str | None
    pathway: ProjectPathway
    status: ProjectStatus
    description: str | None
    original_sqft: float | None
    proposed_sqft: float | None
    stories: int | None
    is_coastal_zone: bool
    is_hillside: bool
    is_very_high_fire_severity: bool
    is_historic: bool
    application_date: datetime | None
    issued_date: datetime | None
    estimated_completion_days: int | None
    predicted_pathway: str | None
    pathway_confidence: float | None
    predicted_days_to_issue: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    clearances: list[ClearanceResponse] = []
