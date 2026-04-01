"""One-shot live data ingestion from LA County public APIs.

Pulls:
1. LADBS permit records from Socrata (data.lacity.org) for Palisades + Altadena zip codes
2. ZIMAS parcel data from the LA City GeoHub ArcGIS service

No API key required — both are public endpoints.

Usage:
    cd backend
    python scripts/ingest_live.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add parent so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = "postgresql+asyncpg://permitai:permitai@localhost:5432/permitai"

SOCRATA_URL = "https://data.lacity.org/resource/hbkd-qubn.json"

# Fire-affected zip codes: Pacific Palisades, Brentwood, Santa Monica adjacent, Altadena
FIRE_ZIPS = ["90272", "90049", "90402", "91001"]

# ZIMAS / ArcGIS parcel endpoint
ZIMAS_PARCEL_URL = (
    "https://public.gis.lacounty.gov/public/rest/services"
    "/LACounty_Cache/LACounty_Parcel/MapServer/0/query"
)

# Bounding boxes for fire-affected areas (minLon,minLat,maxLon,maxLat in WGS84)
FIRE_AREA_BBOXES = [
    {"name": "Pacific Palisades", "bbox": "-118.58,34.02,-118.49,34.08", "coastal": True, "fire": True},
    {"name": "Brentwood", "bbox": "-118.50,34.03,-118.44,34.08", "coastal": False, "fire": False},
    {"name": "Santa Monica adj", "bbox": "-118.52,34.00,-118.47,34.04", "coastal": True, "fire": False},
    {"name": "Altadena / Eaton", "bbox": "-118.18,34.16,-118.10,34.22", "coastal": False, "fire": True},
]

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# 1. Socrata Permit Ingestion
# ---------------------------------------------------------------------------

async def fetch_socrata_permits() -> list[dict]:
    """Fetch all permits from fire-affected zip codes via Socrata public API."""
    all_records = []

    async with httpx.AsyncClient(timeout=60) as client:
        for zip_code in FIRE_ZIPS:
            offset = 0
            page_size = 1000

            while True:
                params = {
                    "$where": f"zip_code='{zip_code}'",
                    "$order": "issue_date DESC",
                    "$limit": str(page_size),
                    "$offset": str(offset),
                }

                try:
                    resp = await client.get(SOCRATA_URL, params=params)
                    if resp.status_code != 200:
                        print(f"  [!] Socrata returned {resp.status_code} for {zip_code}, offset {offset}")
                        break

                    data = resp.json()
                    if not data:
                        break

                    all_records.extend(data)
                    print(f"  [{zip_code}] Fetched {len(data)} records (total: {len(all_records)})")

                    if len(data) < page_size:
                        break
                    offset += page_size

                except Exception as e:
                    print(f"  [!] Error fetching {zip_code}: {e}")
                    break

    return all_records


def transform_permit(raw: dict) -> dict:
    """Transform a Socrata permit record into a projects table row."""
    # Build full address
    parts = [
        raw.get("address_start", ""),
        raw.get("address_fraction", ""),
        raw.get("address_direction", ""),
        raw.get("street_name", ""),
        raw.get("street_suffix", ""),
    ]
    address = " ".join(p for p in parts if p).strip()
    if raw.get("zip_code"):
        address += f", Los Angeles, CA {raw['zip_code']}"

    # Map permit status
    status_map = {
        "CofO Issued": "final",
        "Issued": "issued",
        "Permit Finaled": "final",
        "Ready to Issue": "issued",
        "Plan Check": "in_review",
        "Application Submitted": "intake",
        "PC - Corrections Issued": "in_review",
        "PC - Approved": "approved",
        "Clearances In Process": "in_review",
    }
    status = status_map.get(raw.get("status", ""), "intake")

    # Parse date
    issue_date = None
    if raw.get("issue_date"):
        try:
            issue_date = datetime.fromisoformat(raw["issue_date"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    # Determine pathway based on permit type keywords
    permit_type = (raw.get("permit_type", "") + " " + raw.get("permit_sub_type", "")).upper()
    pathway = None
    if any(kw in permit_type for kw in ["REBUILD", "FIRE", "REPAIR", "RESTORATION"]):
        pathway = "eo1_like_for_like"
    elif "ADDITION" in permit_type or "REMODEL" in permit_type:
        pathway = "eo8_expanded"

    return {
        "id": str(uuid.uuid4()),
        "address": address,
        "apn": raw.get("assessor_parcel_nbr"),
        "owner_id": None,  # Will be set later when users onboard
        "ladbs_permit_number": raw.get("pcis_permit"),
        "status": status,
        "pathway": pathway,
        "original_sqft": None,
        "proposed_sqft": None,
        "stories": None,
        "is_coastal_zone": raw.get("zip_code") == "90272",  # Palisades area
        "is_hillside": False,
        "is_very_high_fire_severity": raw.get("zip_code") in ("90272", "91001"),
        "is_historic": False,
        "is_flood_zone": False,
        "predicted_total_days": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


async def ingest_permits(records: list[dict]) -> int:
    """Insert transformed permit records into the projects table."""
    if not records:
        return 0

    # We need a default owner for permits without a linked user
    default_owner_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "system@permitai.la"))

    async with async_session() as session:
        async with session.begin():
            # Ensure default system user exists
            result = await session.execute(
                text("SELECT id FROM users WHERE id = :uid"),
                {"uid": default_owner_id},
            )
            if not result.scalar():
                await session.execute(
                    text("""
                        INSERT INTO users (id, email, name, role, created_at, updated_at)
                        VALUES (:id, :email, :name, :role, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": default_owner_id,
                        "email": "system@permitai.la",
                        "name": "PermitAI System",
                        "role": "admin",
                    },
                )

    # Prepare all rows first
    rows = []
    skipped = 0
    seen_permits = set()

    for raw in records:
        row = transform_permit(raw)
        permit_num = row.get("ladbs_permit_number")
        if not permit_num or permit_num in seen_permits:
            skipped += 1
            continue
        seen_permits.add(permit_num)
        row["owner_id"] = default_owner_id
        rows.append(row)

    # Batch insert in chunks using executemany-style
    inserted = 0
    batch_size = 500
    errors = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        async with async_session() as batch_session:
            for row in batch:
                try:
                    async with batch_session.begin():
                        await batch_session.execute(
                            text("""
                                INSERT INTO projects (
                                    id, address, apn, owner_id, ladbs_permit_number,
                                    status, pathway, is_coastal_zone, is_hillside,
                                    is_very_high_fire_severity, is_historic, is_flood_zone,
                                    created_at, updated_at
                                ) VALUES (
                                    :id, :address, :apn, :owner_id, :ladbs_permit_number,
                                    :status, :pathway, :is_coastal_zone, :is_hillside,
                                    :is_very_high_fire_severity, :is_historic, :is_flood_zone,
                                    :created_at, :updated_at
                                )
                                ON CONFLICT (ladbs_permit_number) DO UPDATE SET
                                    address = EXCLUDED.address,
                                    status = EXCLUDED.status,
                                    updated_at = EXCLUDED.updated_at
                            """),
                            row,
                        )
                    inserted += 1
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"  [!] Insert error #{errors}: {str(e)[:200]}")

        batch_num = i // batch_size + 1
        if batch_num % 10 == 1:
            print(f"  ... batch {batch_num}: {inserted} inserted, {errors} errors")

    print(f"  Inserted/updated: {inserted}, Errors: {errors}")
    return inserted


# ---------------------------------------------------------------------------
# 2. ZIMAS Parcel Ingestion
# ---------------------------------------------------------------------------

async def fetch_zimas_parcels() -> list[dict]:
    """Fetch parcel data from LA County GeoHub for fire-affected areas.

    Uses spatial bounding-box queries for much better coverage than zip
    code filtering.  outFields=* with returnGeometry=false because the
    ArcGIS endpoint fails with specific field lists + geometry.  We use
    CENTER_LAT / CENTER_LON attribute columns for PostGIS points instead.
    """
    all_features = []

    async with httpx.AsyncClient(timeout=120) as client:
        for area in FIRE_AREA_BBOXES:
            offset = 0
            page_size = 1000
            area_count = 0

            while True:
                params = {
                    "geometry": area["bbox"],
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "f": "json",
                    "resultRecordCount": str(page_size),
                    "resultOffset": str(offset),
                    "returnGeometry": "false",
                }

                try:
                    resp = await client.get(ZIMAS_PARCEL_URL, params=params)
                    if resp.status_code != 200:
                        print(f"  [!] ZIMAS returned {resp.status_code} for {area['name']}")
                        break

                    data = resp.json()

                    if "error" in data:
                        print(f"  [!] ZIMAS error for {area['name']}: {data['error'].get('message', 'unknown')}")
                        break

                    features = data.get("features", [])
                    # Tag each feature with the area flags for transform
                    for f in features:
                        f["_area_coastal"] = area["coastal"]
                        f["_area_fire"] = area["fire"]

                    all_features.extend(features)
                    area_count += len(features)
                    print(f"  [{area['name']}] page {offset // page_size + 1}: {len(features)} parcels (area total: {area_count})")

                    if len(features) < page_size:
                        break
                    offset += page_size

                except Exception as e:
                    print(f"  [!] Error fetching parcels for {area['name']}: {e}")
                    break

            print(f"  [{area['name']}] DONE: {area_count} parcels")

    return all_features


def transform_parcel(feature: dict) -> dict | None:
    """Transform an ArcGIS parcel feature into a parcels table row.

    Field names in the LA County Assessor Parcels dataset use numeric
    suffixes (e.g. SQFTmain1, YearBuilt1, Bedrooms1, Bathrooms1).
    Geometry comes from CENTER_LAT / CENTER_LON attributes since we
    fetch with returnGeometry=false.
    """
    attrs = feature.get("attributes", {})

    apn = attrs.get("APN")
    if not apn:
        return None

    apn = str(apn).strip().replace("-", "")  # normalise "4408-016-016" -> "4408016016"

    # Build POINT geometry from centroid lat/lon
    lat = attrs.get("CENTER_LAT")
    lon = attrs.get("CENTER_LON")
    wkt = None
    if lat and lon:
        try:
            wkt = f"SRID=4326;POINT({float(lon)} {float(lat)})"
        except (ValueError, TypeError):
            pass

    # Lot area: prefer Shape.STArea() (sq ft of parcel polygon), fall back to SQFTmain1
    lot_area = None
    for key in ("Shape.STArea()", "Shape_STArea", "SQFTmain1", "SQFTmain"):
        val = attrs.get(key)
        if val is not None:
            try:
                lot_area = float(val)
                if lot_area > 0:
                    break
            except (ValueError, TypeError):
                continue

    # Use UseType + UseDescription for zone info
    use_type = attrs.get("UseType", "")
    use_desc = attrs.get("UseDescription", "")
    zone_class = f"{use_type}/{use_desc}".strip("/") if use_type or use_desc else None

    return {
        "apn": apn,
        "zone_class": zone_class,
        "lot_area_sqft": lot_area,
        "council_district": None,
        "is_coastal_zone": bool(feature.get("_area_coastal", False)),
        "is_hillside": False,
        "is_very_high_fire_severity": bool(feature.get("_area_fire", False)),
        "is_historic": False,
        "is_flood_zone": False,
        "geom": wkt,
        "zimas_last_sync": datetime.now(timezone.utc),
    }


async def ingest_parcels(features: list[dict]) -> int:
    """Insert parcel data into the parcels table."""
    if not features:
        return 0

    # Pre-transform and deduplicate
    rows = []
    seen_apns: set[str] = set()
    transform_skipped = 0

    for feature in features:
        row = transform_parcel(feature)
        if not row:
            transform_skipped += 1
            continue
        if row["apn"] in seen_apns:
            transform_skipped += 1
            continue
        seen_apns.add(row["apn"])
        rows.append(row)

    print(f"  Transformed {len(rows)} unique parcels, skipped {transform_skipped}")

    inserted = 0
    errors = 0

    for row in rows:
        geom_val = row.pop("geom", None)
        async with async_session() as session:
            try:
                async with session.begin():
                    if geom_val:
                        await session.execute(
                            text("""
                                INSERT INTO parcels (
                                    apn, zone_class, lot_area_sqft,
                                    council_district, is_coastal_zone, is_hillside,
                                    is_very_high_fire_severity, is_historic,
                                    is_flood_zone, geom, zimas_last_sync,
                                    created_at, updated_at
                                ) VALUES (
                                    :apn, :zone_class, :lot_area_sqft,
                                    :council_district, :is_coastal_zone, :is_hillside,
                                    :is_very_high_fire_severity, :is_historic,
                                    :is_flood_zone, ST_GeomFromEWKT(:geom),
                                    :zimas_last_sync, NOW(), NOW()
                                )
                                ON CONFLICT (apn) DO UPDATE SET
                                    zone_class = EXCLUDED.zone_class,
                                    lot_area_sqft = EXCLUDED.lot_area_sqft,
                                    geom = EXCLUDED.geom,
                                    is_coastal_zone = EXCLUDED.is_coastal_zone,
                                    is_very_high_fire_severity = EXCLUDED.is_very_high_fire_severity,
                                    zimas_last_sync = EXCLUDED.zimas_last_sync,
                                    updated_at = NOW()
                            """),
                            {**row, "geom": geom_val},
                        )
                    else:
                        await session.execute(
                            text("""
                                INSERT INTO parcels (
                                    apn, zone_class, lot_area_sqft,
                                    council_district, is_coastal_zone, is_hillside,
                                    is_very_high_fire_severity, is_historic,
                                    is_flood_zone, zimas_last_sync,
                                    created_at, updated_at
                                ) VALUES (
                                    :apn, :zone_class, :lot_area_sqft,
                                    :council_district, :is_coastal_zone, :is_hillside,
                                    :is_very_high_fire_severity, :is_historic,
                                    :is_flood_zone, :zimas_last_sync, NOW(), NOW()
                                )
                                ON CONFLICT (apn) DO UPDATE SET
                                    zone_class = EXCLUDED.zone_class,
                                    lot_area_sqft = EXCLUDED.lot_area_sqft,
                                    is_coastal_zone = EXCLUDED.is_coastal_zone,
                                    is_very_high_fire_severity = EXCLUDED.is_very_high_fire_severity,
                                    zimas_last_sync = EXCLUDED.zimas_last_sync,
                                    updated_at = NOW()
                            """),
                            row,
                        )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [!] Parcel insert error #{errors}: {str(e)[:200]}")

        if inserted % 100 == 0 and inserted > 0:
            print(f"  ... {inserted} parcels inserted so far, {errors} errors")

    print(f"  Parcels inserted/updated: {inserted}, Errors: {errors}")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("PermitAI LA — Live Data Ingestion")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Target zip codes: {', '.join(FIRE_ZIPS)}")
    print("=" * 60)

    # 1. Socrata Permits
    print("\n[1/2] Fetching LADBS permits from Socrata (data.lacity.org)...")
    permits = await fetch_socrata_permits()
    print(f"  Total permits fetched: {len(permits)}")

    if permits:
        print("  Loading into database...")
        count = await ingest_permits(permits)
        print(f"  >>{count} permit records loaded into projects table")

    # 2. ZIMAS Parcels
    print("\n[2/2] Fetching parcel data from LA County GeoHub...")
    parcels = await fetch_zimas_parcels()
    print(f"  Total parcels fetched: {len(parcels)}")

    if parcels:
        print("  Loading into database...")
        count = await ingest_parcels(parcels)
        print(f"  >>{count} parcel records loaded into parcels table")

    # Summary
    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM projects"))
        project_count = result.scalar()
        result = await session.execute(text("SELECT COUNT(*) FROM parcels"))
        parcel_count = result.scalar()

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"  Projects in DB: {project_count}")
    print(f"  Parcels in DB:  {parcel_count}")
    print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
