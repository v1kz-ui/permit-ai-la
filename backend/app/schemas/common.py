import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Enums matching database values ---


class ProjectPathway(str, enum.Enum):
    EO1_LIKE_FOR_LIKE = "eo1_like_for_like"
    EO8_EXPANDED = "eo8_expanded"
    STANDARD = "standard"
    SELF_CERTIFICATION = "self_certification"
    UNKNOWN = "unknown"


class ProjectStatus(str, enum.Enum):
    INTAKE = "intake"
    IN_REVIEW = "in_review"
    PLAN_CHECK = "plan_check"
    CLEARANCES_IN_PROGRESS = "clearances_in_progress"
    APPROVED = "approved"
    READY_FOR_ISSUE = "ready_for_issue"
    ISSUED = "issued"
    INSPECTION = "inspection"
    FINAL = "final"
    CLOSED = "closed"


class ClearanceDepartment(str, enum.Enum):
    LADBS = "ladbs"
    DCP = "dcp"
    BOE = "boe"
    LAFD = "lafd"
    LADWP = "ladwp"
    LASAN = "lasan"
    LAHD = "lahd"
    DOT = "dot"
    CULTURAL_AFFAIRS = "cultural_affairs"
    URBAN_FORESTRY = "urban_forestry"
    LA_COUNTY = "la_county"


class ClearanceStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    DENIED = "denied"
    NOT_APPLICABLE = "not_applicable"


class InspectionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    PASSED = "passed"
    FAILED = "failed"
    COMPLETED_PASS = "completed_pass"
    COMPLETED_FAIL = "completed_fail"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class DocumentType(str, enum.Enum):
    PERMIT_APPLICATION = "permit_application"
    ARCHITECTURAL_PLAN = "architectural_plan"
    STRUCTURAL_PLAN = "structural_plan"
    SURVEY = "survey"
    SOILS_REPORT = "soils_report"
    PHOTO = "photo"
    CLEARANCE_LETTER = "clearance_letter"
    INSPECTION_REPORT = "inspection_report"
    OTHER = "other"


class UserRole(str, enum.Enum):
    HOMEOWNER = "homeowner"
    CONTRACTOR = "contractor"
    ARCHITECT = "architect"
    STAFF = "staff"
    ADMIN = "admin"


class Language(str, enum.Enum):
    EN = "en"
    ES = "es"
    KO = "ko"
    ZH = "zh"
    TL = "tl"


class NotificationType(str, enum.Enum):
    CLEARANCE_STATUS_CHANGED = "clearance_status_changed"
    INSPECTION_SCHEDULED = "inspection_scheduled"
    INSPECTION_RESULT = "inspection_result"
    DOCUMENT_REQUIRED = "document_required"
    PERMIT_STATUS_CHANGED = "permit_status_changed"
    BOTTLENECK_DETECTED = "bottleneck_detected"


class NotificationChannel(str, enum.Enum):
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


# --- Shared Pydantic models ---


class PaginationParams(BaseModel):
    page: int = 1
    size: int = 20


class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 0


class ErrorDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None


class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseModel):
    id: UUID
