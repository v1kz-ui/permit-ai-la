from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Parcel(Base):
    __tablename__ = "parcels"

    apn: Mapped[str] = mapped_column(String(20), primary_key=True)
    geom: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326), nullable=True, index=True
    )

    # Address
    address: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)

    # Zoning
    zone_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    zone_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    general_plan_land_use: Mapped[str | None] = mapped_column(String(100), nullable=True)
    height_district: Mapped[str | None] = mapped_column(String(20), nullable=True)
    specific_plan: Mapped[str | None] = mapped_column(String(200), nullable=True)
    community_plan_area: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Overlays and flags
    is_coastal_zone: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hillside: Mapped[bool] = mapped_column(Boolean, default=False)
    is_very_high_fire_severity: Mapped[bool] = mapped_column(Boolean, default=False)
    is_flood_zone: Mapped[bool] = mapped_column(Boolean, default=False)
    is_geological_hazard: Mapped[bool] = mapped_column(Boolean, default=False)
    is_historic: Mapped[bool] = mapped_column(Boolean, default=False)
    has_hpoz: Mapped[bool] = mapped_column(Boolean, default=False)

    # Lot dimensions
    lot_area_sqft: Mapped[float | None] = mapped_column(Float, nullable=True)
    lot_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    lot_depth: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Council info
    council_district: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sync tracking
    zimas_last_sync: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
