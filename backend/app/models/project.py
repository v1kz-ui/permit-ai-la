import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.common import ProjectPathway, ProjectStatus

if TYPE_CHECKING:
    from app.models.clearance import Clearance
    from app.models.document import Document
    from app.models.inspection import Inspection
    from app.models.user import User


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    # Location
    address: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    apn: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Owner
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Permit info
    ladbs_permit_number: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, index=True
    )
    pathway: Mapped[str] = mapped_column(
        ENUM(ProjectPathway, name="project_pathway", create_type=True),
        nullable=False,
        default=ProjectPathway.UNKNOWN,
    )
    status: Mapped[str] = mapped_column(
        ENUM(ProjectStatus, name="project_status", create_type=True),
        nullable=False,
        default=ProjectStatus.INTAKE,
    )

    # Scope
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_sqft: Mapped[float | None] = mapped_column(Float, nullable=True)
    proposed_sqft: Mapped[float | None] = mapped_column(Float, nullable=True)
    stories: Mapped[int | None] = mapped_column(nullable=True)

    # Parcel flags (denormalized from parcels table for query speed)
    is_coastal_zone: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hillside: Mapped[bool] = mapped_column(Boolean, default=False)
    is_very_high_fire_severity: Mapped[bool] = mapped_column(Boolean, default=False)
    is_historic: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timeline
    application_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    issued_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_completion_days: Mapped[int | None] = mapped_column(nullable=True)

    # AI predictions
    predicted_pathway: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pathway_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_days_to_issue: Mapped[int | None] = mapped_column(nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="projects", lazy="selectin")
    clearances: Mapped[list["Clearance"]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", lazy="noload", cascade="all, delete-orphan"
    )
