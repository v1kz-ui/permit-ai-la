from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ClearanceDepartment, ClearanceStatus


class ClearanceCreate(BaseModel):
    project_id: UUID
    department: ClearanceDepartment
    clearance_type: str
    status: ClearanceStatus = ClearanceStatus.NOT_STARTED


class ClearanceUpdate(BaseModel):
    status: ClearanceStatus | None = None
    is_bottleneck: bool | None = None
    assigned_to: str | None = None
    notes: str | None = None


class ClearanceResponse(BaseModel):
    id: UUID
    project_id: UUID
    department: ClearanceDepartment
    clearance_type: str
    status: ClearanceStatus
    is_bottleneck: bool
    assigned_to: str | None
    notes: str | None
    conflict_with_id: UUID | None
    conflict_description: str | None
    submitted_date: datetime | None
    completed_date: datetime | None
    predicted_days: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
