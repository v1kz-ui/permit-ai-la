from datetime import datetime

from pydantic import BaseModel


class ParcelResponse(BaseModel):
    apn: str
    address: str | None
    zone_class: str | None
    zone_summary: str | None
    general_plan_land_use: str | None
    height_district: str | None
    specific_plan: str | None
    community_plan_area: str | None
    is_coastal_zone: bool
    is_hillside: bool
    is_very_high_fire_severity: bool
    is_flood_zone: bool
    is_geological_hazard: bool
    is_historic: bool
    has_hpoz: bool
    lot_area_sqft: float | None
    lot_width: float | None
    lot_depth: float | None
    council_district: int | None
    zimas_last_sync: datetime | None

    model_config = {"from_attributes": True}


class ParcelLookupQuery(BaseModel):
    lat: float
    lng: float
