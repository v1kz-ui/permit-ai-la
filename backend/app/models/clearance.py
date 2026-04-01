import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.common import ClearanceDepartment, ClearanceStatus


class Clearance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clearances"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    department: Mapped[str] = mapped_column(
        ENUM(ClearanceDepartment, name="clearance_department", create_type=True),
        nullable=False,
    )
    clearance_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        ENUM(ClearanceStatus, name="clearance_status", create_type=True),
        nullable=False,
        default=ClearanceStatus.NOT_STARTED,
    )

    # Tracking
    is_bottleneck: Mapped[bool] = mapped_column(default=False)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Conflict tracking
    conflict_with_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clearances.id"), nullable=True
    )
    conflict_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timeline
    submitted_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    predicted_days: Mapped[int | None] = mapped_column(nullable=True)

    # PCIS sync
    pcis_case_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pcis_last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="clearances")
    conflict_with = relationship("Clearance", remote_side="Clearance.id", uselist=False)

    __table_args__ = (
        # Composite index for fast lookups by project + department
        {"comment": "idx_clearances_project_dept is on (project_id, department)"},
    )
