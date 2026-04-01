"""ZIMAS parcel upsert logic with PostGIS geometry conversion.

Handles the full pipeline:
  ArcGIS GeoJSON feature → Parcel model column dict → PostgreSQL upsert

The critical step this module handles that the generic loader does NOT is
converting the raw GeoJSON geometry dict (from ArcGIS) into a Well-Known
Text (WKT) string that GeoAlchemy2 / PostGIS can consume.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parcel import Parcel

logger = structlog.get_logger(__name__)

# ArcGIS "yes/no" coded values that map to True
_TRUTHY = {1, "1", "Yes", "YES", "yes", "Y", "y", True}

# Community plan areas to refresh (both fire-affected communities)
COMMUNITY_PLAN_AREAS = [
    "Palisades",
    "Altadena",           # Unincorporated LA County; same ArcGIS service
]


def _geojson_to_wkt(geometry: dict[str, Any] | None) -> str | None:
    """Convert a GeoJSON geometry dict to a WKT string for PostGIS.

    Handles Point, Polygon, MultiPolygon.  Returns None if geometry is
    missing or cannot be parsed.  We use string construction rather than
    Shapely to avoid the dependency in this path (Shapely is heavy).
    """
    if not geometry:
        return None

    try:
        geo_type = geometry.get("type", "")
        coordinates = geometry.get("coordinates")
        if not coordinates:
            return None

        if geo_type == "Point":
            lng, lat = coordinates[0], coordinates[1]
            return f"SRID=4326;POINT({lng} {lat})"

        if geo_type == "Polygon":
            rings = []
            for ring in coordinates:
                pts = ", ".join(f"{x} {y}" for x, y in ring)
                rings.append(f"({pts})")
            return f"SRID=4326;POLYGON({', '.join(rings)})"

        if geo_type == "MultiPolygon":
            polys = []
            for poly in coordinates:
                rings = []
                for ring in poly:
                    pts = ", ".join(f"{x} {y}" for x, y in ring)
                    rings.append(f"({pts})")
                polys.append(f"({', '.join(rings)})")
            return f"SRID=4326;MULTIPOLYGON({', '.join(polys)})"

        # Fallback: try Shapely if available
        try:
            import shapely.geometry as sg
            from shapely import wkt as shapely_wkt

            shape = sg.shape(geometry)
            return f"SRID=4326;{shapely_wkt.dumps(shape)}"
        except ImportError:
            pass

        logger.warning("zimas_loader.unsupported_geometry_type", geo_type=geo_type)
        return None

    except Exception as exc:
        logger.warning("zimas_loader.geometry_parse_error", error=str(exc))
        return None


def map_feature_to_row(feature: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a raw ArcGIS GeoJSON feature dict to a Parcel upsert row.

    Returns None if the feature lacks an APN (the primary key).
    """
    apn = feature.get("APN") or feature.get("apn")
    if not apn:
        return None

    # Normalize the APN: strip spaces, standardise format
    apn = str(apn).strip().replace(" ", "-")

    # Convert geometry
    raw_geom = feature.get("_geometry") or feature.get("geometry")
    wkt_geom = _geojson_to_wkt(raw_geom)

    def as_bool(val: Any) -> bool:
        return val in _TRUTHY

    def as_float(val: Any) -> float | None:
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def as_int(val: Any) -> int | None:
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    row: dict[str, Any] = {
        "apn": apn,
        "address": feature.get("SitusAddress"),
        "zone_class": feature.get("ZoneClass"),
        "general_plan_land_use": feature.get("GeneralPlanLandUse"),
        "height_district": feature.get("HeightDistrict"),
        "specific_plan": feature.get("SpecificPlan") or None,
        "community_plan_area": feature.get("CommunityPlanArea"),
        "is_coastal_zone": as_bool(feature.get("CoastalZone")),
        "is_hillside": as_bool(feature.get("Hillside")),
        "is_very_high_fire_severity": as_bool(feature.get("VeryHighFireSeverity")),
        "is_flood_zone": as_bool(feature.get("FloodZone")),
        "is_geological_hazard": as_bool(feature.get("GeologicalHazard")),
        "is_historic": as_bool(feature.get("Historic")),
        "has_hpoz": as_bool(feature.get("HPOZ")),
        "lot_area_sqft": as_float(feature.get("LotAreaSqFt")),
        "lot_width": as_float(feature.get("LotWidth")),
        "lot_depth": as_float(feature.get("LotDepth")),
        "council_district": as_int(feature.get("CouncilDistrict")),
        "zimas_last_sync": datetime.now(timezone.utc),
    }

    # Only include geometry if we successfully converted it
    if wkt_geom:
        row["geom"] = wkt_geom

    return row


async def upsert_parcels(
    session: AsyncSession,
    features: list[dict[str, Any]],
) -> tuple[int, int]:
    """Upsert a batch of ZIMAS feature dicts into the ``parcels`` table.

    Returns (rows_upserted, rows_skipped).
    """
    rows: list[dict[str, Any]] = []
    skipped = 0

    for feature in features:
        row = map_feature_to_row(feature)
        if row is None:
            skipped += 1
            continue
        rows.append(row)

    if not rows:
        logger.warning("zimas_loader.no_valid_rows", total_features=len(features))
        return 0, skipped

    # Columns to update on conflict — everything except the PK
    update_cols = [k for k in rows[0] if k != "apn"]

    stmt = pg_insert(Parcel).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["apn"],
        set_={col: getattr(stmt.excluded, col) for col in update_cols},
    )

    result = await session.execute(stmt)
    await session.flush()

    upserted = result.rowcount  # type: ignore[union-attr]
    logger.info(
        "zimas_loader.upsert_complete",
        upserted=upserted,
        skipped=skipped,
        batch_size=len(features),
    )
    return upserted, skipped
