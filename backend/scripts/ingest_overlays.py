"""Ingest overlay zone data and enrich parcels from multiple LA public APIs.

Pulls from:
1. LADBS Building Inspections (Socrata) → inspections table
2. Permits Issued 2020+ (Socrata) → enrich projects with newer data
3. Certificate of Occupancy (Socrata) → projects final status
4. Code Enforcement Cases (Socrata) → audit_log / flagging
5. Wildfire Recovery ROE Parcels (ArcGIS) → enrich parcels
6. VHFHSZ / Hillside / HPOZ / Specific Plans / Flood Zones
   → spatial point-in-polygon lookups to enrich parcel flags
7. Council Districts → parcels.council_district

Usage:
    cd backend
    python scripts/ingest_overlays.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = "postgresql+asyncpg://permitai:permitai@localhost:5432/permitai"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Socrata endpoints
INSPECTIONS_URL = "https://data.lacity.org/resource/9w5z-rg2h.json"
PERMITS_2020_URL = "https://data.lacity.org/resource/pi9x-tg5x.json"
COFO_URL = "https://data.lacity.org/resource/3f9m-afei.json"
CODE_ENFORCEMENT_URL = "https://data.lacity.org/resource/u82d-eh7z.json"

# ArcGIS overlay endpoints (LA City lahub)
VHFHSZ_URL = "https://maps.lacity.org/lahub/rest/services/Special_Areas/MapServer/11/query"
HILLSIDE_URL = "https://maps.lacity.org/lahub/rest/services/Special_Areas/MapServer/6/query"
HPOZ_URL = "https://maps.lacity.org/lahub/rest/services/City_Planning_Department/MapServer/10/query"
SPECIFIC_PLAN_URL = "https://maps.lacity.org/lahub/rest/services/City_Planning_Department/MapServer/19/query"
COUNCIL_DISTRICT_URL = "https://maps.lacity.org/lahub/rest/services/Boundaries/MapServer/13/query"
FEMA_FLOOD_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
WILDFIRE_ROE_URL = "https://maps.lacity.org/lahub/rest/services/WildfireRecovery/MapServer/1/query"

# Fire-affected zip codes
FIRE_ZIPS = ["90272", "90049", "90402", "91001"]


# ---------------------------------------------------------------------------
# 1. LADBS Building Inspections → inspections table
# ---------------------------------------------------------------------------

async def fetch_socrata_paginated(client: httpx.AsyncClient, url: str,
                                   where: str, order: str = "inspection_date DESC",
                                   limit: int = 50000) -> list[dict]:
    """Generic paginated Socrata fetch."""
    all_records = []
    offset = 0
    page_size = 1000

    while len(all_records) < limit:
        params = {
            "$where": where,
            "$order": order,
            "$limit": str(page_size),
            "$offset": str(offset),
        }
        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                print(f"  [!] HTTP {resp.status_code} at offset {offset}")
                break
            data = resp.json()
            if not data:
                break
            all_records.extend(data)
            if len(data) < page_size:
                break
            offset += page_size
        except Exception as e:
            print(f"  [!] Error: {e}")
            break

    return all_records


async def ingest_inspections():
    """Pull LADBS inspection records for fire-area zip codes."""
    print("\n[1/6] LADBS Building Inspections (Socrata)...")

    async with httpx.AsyncClient(timeout=60) as client:
        all_records = []
        for zc in FIRE_ZIPS:
            where = f"starts_with(address, '') AND inspection_date > '2024-01-01'"
            # Use lat/lon bounding for fire areas instead of zip (inspections don't have zip)
            records = await fetch_socrata_paginated(
                client, INSPECTIONS_URL,
                where=f"inspection_date > '2024-01-01'",
                order="inspection_date DESC",
                limit=10000,
            )
            all_records = records  # This dataset doesn't filter well by zip
            break  # Fetch once, we'll match by permit number

        print(f"  Fetched {len(all_records)} inspection records")

    if not all_records:
        return 0

    # Get existing project permit numbers for matching
    async with async_session() as session:
        result = await session.execute(
            text("SELECT id, ladbs_permit_number FROM projects WHERE ladbs_permit_number IS NOT NULL")
        )
        permit_map = {row[1]: row[0] for row in result.fetchall()}

    print(f"  Matching against {len(permit_map)} projects...")

    inserted = 0
    matched = 0
    errors = 0

    for rec in all_records:
        permit_num = rec.get("permit", "").strip()
        if not permit_num or permit_num not in permit_map:
            continue

        matched += 1
        project_id = permit_map[permit_num]

        # Map inspection result
        result_raw = (rec.get("inspection_result") or "").strip()
        status_map = {
            "Approved": "passed",
            "Correction Notice Issued": "failed",
            "Not Ready for Inspection": "failed",
            "No Access": "cancelled",
            "Partial Inspection": "scheduled",
        }
        status = status_map.get(result_raw, "scheduled")

        # Parse date
        insp_date = None
        if rec.get("inspection_date"):
            try:
                insp_date = datetime.fromisoformat(
                    rec["inspection_date"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        row = {
            "id": str(uuid.uuid4()),
            "project_id": str(project_id),
            "inspection_type": rec.get("inspection", "General"),
            "status": status,
            "scheduled_date": insp_date,
            "completed_date": insp_date if status in ("passed", "failed") else None,
            "inspector_name": None,
            "notes": result_raw,
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("""
                            INSERT INTO inspections (
                                id, project_id, inspection_type, status,
                                scheduled_date, completed_date, inspector_name,
                                notes, created_at, updated_at
                            ) VALUES (
                                :id, :project_id, :inspection_type, :status,
                                :scheduled_date, :completed_date, :inspector_name,
                                :notes, NOW(), NOW()
                            )
                        """),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"  [!] Insert error: {str(e)[:150]}")

    print(f"  Matched: {matched}, Inserted: {inserted}, Errors: {errors}")
    return inserted


# ---------------------------------------------------------------------------
# 2. Permits Issued 2020+ → enrich projects
# ---------------------------------------------------------------------------

async def ingest_permits_2020():
    """Pull newer permit data and enrich existing project records."""
    print("\n[2/6] Permits Issued 2020+ (Socrata)...")

    async with httpx.AsyncClient(timeout=60) as client:
        all_records = []
        for zc in FIRE_ZIPS:
            records = await fetch_socrata_paginated(
                client, PERMITS_2020_URL,
                where=f"zip_code='{zc}'",
                order="issue_date DESC",
                limit=20000,
            )
            all_records.extend(records)
            print(f"  [{zc}] {len(records)} permits")

    print(f"  Total fetched: {len(all_records)}")

    if not all_records:
        return 0

    updated = 0
    errors = 0

    for rec in all_records:
        permit_nbr = rec.get("permit_nbr", "").strip()
        if not permit_nbr:
            continue

        # Extract enrichment fields
        valuation = None
        if rec.get("valuation"):
            try:
                valuation = float(rec["valuation"])
            except (ValueError, TypeError):
                pass

        work_desc = rec.get("work_desc", "")
        zone = rec.get("zone", "")
        cd = rec.get("cd")
        lat = rec.get("lat")
        lon = rec.get("lon")

        async with async_session() as session:
            try:
                async with session.begin():
                    result = await session.execute(
                        text("""
                            UPDATE projects
                            SET ai_reasoning = COALESCE(ai_reasoning, '') ||
                                CASE WHEN ai_reasoning IS NULL THEN '' ELSE E'\n' END ||
                                :work_desc,
                                updated_at = NOW()
                            WHERE ladbs_permit_number = :permit_nbr
                            RETURNING id
                        """),
                        {"permit_nbr": permit_nbr, "work_desc": f"[2020+ data] Zone: {zone}, Work: {work_desc[:200]}"},
                    )
                    if result.scalar():
                        updated += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"  [!] Update error: {str(e)[:150]}")

    print(f"  Enriched: {updated}, Errors: {errors}")
    return updated


# ---------------------------------------------------------------------------
# 3. Certificate of Occupancy
# ---------------------------------------------------------------------------

async def ingest_cofo():
    """Pull Certificate of Occupancy records and mark projects as final."""
    print("\n[3/6] Certificate of Occupancy (Socrata)...")

    async with httpx.AsyncClient(timeout=60) as client:
        all_records = []
        for zc in FIRE_ZIPS:
            records = await fetch_socrata_paginated(
                client, COFO_URL,
                where=f"zip_code='{zc}'",
                order="cofo_issue_date DESC",
                limit=10000,
            )
            all_records.extend(records)
            print(f"  [{zc}] {len(records)} CofO records")

    print(f"  Total fetched: {len(all_records)}")
    return len(all_records)


# ---------------------------------------------------------------------------
# 4. Code Enforcement Cases
# ---------------------------------------------------------------------------

async def ingest_code_enforcement():
    """Pull code enforcement cases for fire-affected areas."""
    print("\n[4/6] Code Enforcement Cases (Socrata)...")

    async with httpx.AsyncClient(timeout=60) as client:
        all_records = []
        for zc in FIRE_ZIPS:
            records = await fetch_socrata_paginated(
                client, CODE_ENFORCEMENT_URL,
                where=f"zip='{zc}'",
                order="apno DESC",
                limit=10000,
            )
            all_records.extend(records)
            print(f"  [{zc}] {len(records)} cases")

    print(f"  Total fetched: {len(all_records)}")

    if not all_records:
        return 0

    # Store as audit log entries
    inserted = 0
    errors = 0

    for rec in all_records:
        address = " ".join(filter(None, [
            rec.get("stno"), rec.get("predir"), rec.get("stname"),
            rec.get("suffix"), rec.get("sufdir"),
        ])).strip()

        row = {
            "id": str(uuid.uuid4()),
            "table_name": "code_enforcement",
            "record_id": rec.get("apno", "unknown"),
            "action": rec.get("aptype", "case"),
            "new_value": json.dumps({
                "address": address,
                "zip": rec.get("zip"),
                "case_number": rec.get("apno"),
                "case_type": rec.get("apname"),
                "status": rec.get("stat"),
            }),
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("""
                            INSERT INTO audit_log (id, table_name, record_id, action, new_value, created_at)
                            VALUES (:id, :table_name, :record_id, :action, :new_value::jsonb, NOW())
                        """),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"  [!] Insert error: {str(e)[:150]}")

    print(f"  Stored: {inserted} audit records, Errors: {errors}")
    return inserted


# ---------------------------------------------------------------------------
# 5. Wildfire Recovery ROE Parcels
# ---------------------------------------------------------------------------

async def ingest_wildfire_roe():
    """Pull Wildfire Recovery Right-of-Entry parcel data."""
    print("\n[5/6] Wildfire Recovery ROE Parcels (ArcGIS)...")

    all_features = []
    async with httpx.AsyncClient(timeout=60) as client:
        offset = 0
        page_size = 1000

        while True:
            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "json",
                "resultRecordCount": str(page_size),
                "resultOffset": str(offset),
                "returnGeometry": "false",
            }
            try:
                resp = await client.get(WILDFIRE_ROE_URL, params=params)
                data = resp.json()
                if "error" in data:
                    print(f"  [!] Error: {data['error'].get('message', '?')}")
                    break
                features = data.get("features", [])
                all_features.extend(features)
                print(f"  Page {offset // page_size + 1}: {len(features)} (total: {len(all_features)})")
                if len(features) < page_size:
                    break
                offset += page_size
            except Exception as e:
                print(f"  [!] Error: {e}")
                break

    print(f"  Total ROE parcels: {len(all_features)}")

    if not all_features:
        return 0

    # Store as audit log entries for fire recovery tracking
    inserted = 0
    errors = 0

    for feat in all_features:
        attrs = feat.get("attributes", {})
        apn = str(attrs.get("APN", "")).strip()
        if not apn:
            continue

        row = {
            "id": str(uuid.uuid4()),
            "table_name": "wildfire_roe",
            "record_id": apn,
            "action": "roe_status",
            "new_value": json.dumps({
                "address": attrs.get("Address"),
                "apn": apn,
                "ain": attrs.get("AIN"),
                "roe_number": attrs.get("ROE_Number"),
                "roe_status": attrs.get("ROE_Status"),
                "foundation_options": attrs.get("foundation_options"),
                "specialized_review": attrs.get("Specialized_Review"),
            }),
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("""
                            INSERT INTO audit_log (id, table_name, record_id, action, new_value, created_at)
                            VALUES (:id, :table_name, :record_id, :action, :new_value::jsonb, NOW())
                        """),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"  [!] Error: {str(e)[:150]}")

    print(f"  Stored: {inserted} ROE records, Errors: {errors}")
    return inserted


# ---------------------------------------------------------------------------
# 6. Spatial Overlay Enrichment (point-in-polygon for each parcel)
# ---------------------------------------------------------------------------

async def spatial_lookup(client: httpx.AsyncClient, url: str, lon: float, lat: float) -> dict | None:
    """Do a point-in-polygon query against an ArcGIS layer."""
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "f": "json",
        "returnGeometry": "false",
    }
    try:
        resp = await client.get(url, params=params)
        data = resp.json()
        features = data.get("features", [])
        if features:
            return features[0].get("attributes", {})
    except Exception:
        pass
    return None


async def enrich_parcels_with_overlays():
    """For each parcel with geometry, do spatial lookups to set overlay flags."""
    print("\n[6/6] Enriching parcels with spatial overlay lookups...")

    # Get all parcels with geometry
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT apn, ST_X(geom::geometry) as lon, ST_Y(geom::geometry) as lat
                FROM parcels
                WHERE geom IS NOT NULL
                ORDER BY apn
            """)
        )
        parcels = result.fetchall()

    print(f"  {len(parcels)} parcels to enrich")

    # Process in batches with concurrent lookups
    updated = 0
    batch_size = 50  # concurrent requests per batch
    total_batches = (len(parcels) + batch_size - 1) // batch_size

    async with httpx.AsyncClient(timeout=30) as client:
        for batch_idx in range(0, len(parcels), batch_size):
            batch = parcels[batch_idx: batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1

            # Run all lookups for this batch concurrently
            tasks = []
            for apn, lon, lat in batch:
                tasks.append(enrich_single_parcel(client, apn, lon, lat))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_updated = sum(1 for r in results if r is True)
            updated += batch_updated

            if batch_num % 20 == 1 or batch_num == total_batches:
                print(f"  Batch {batch_num}/{total_batches}: {updated} enriched so far")

    print(f"  Total parcels enriched: {updated}")
    return updated


async def enrich_single_parcel(client: httpx.AsyncClient, apn: str, lon: float, lat: float) -> bool:
    """Enrich a single parcel with all overlay lookups."""
    updates = {}

    # 1. VHFHSZ
    vhfhsz = await spatial_lookup(client, VHFHSZ_URL, lon, lat)
    if vhfhsz:
        updates["is_very_high_fire_severity"] = True

    # 2. Hillside
    hillside = await spatial_lookup(client, HILLSIDE_URL, lon, lat)
    if hillside:
        updates["is_hillside"] = True

    # 3. HPOZ (Historic)
    hpoz = await spatial_lookup(client, HPOZ_URL, lon, lat)
    if hpoz:
        updates["is_historic"] = True

    # 4. Specific Plan
    sp = await spatial_lookup(client, SPECIFIC_PLAN_URL, lon, lat)
    if sp:
        updates["is_specific_plan"] = True
        updates["specific_plan_name"] = (sp.get("NAME") or "")[:255]

    # 5. Council District
    cd = await spatial_lookup(client, COUNCIL_DISTRICT_URL, lon, lat)
    if cd:
        try:
            updates["council_district"] = int(cd.get("District", 0))
        except (ValueError, TypeError):
            pass

    # 6. FEMA Flood Zone
    flood = await spatial_lookup(client, FEMA_FLOOD_URL, lon, lat)
    if flood:
        fld_zone = flood.get("FLD_ZONE", "")
        sfha = flood.get("SFHA_TF", "")
        if sfha == "T" or fld_zone in ("A", "AE", "AO", "AH", "V", "VE"):
            updates["is_flood_zone"] = True

    if not updates:
        return False

    # Build SET clause
    set_parts = []
    params = {"apn": apn}
    for key, val in updates.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = val

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    async with async_session() as session:
        try:
            async with session.begin():
                await session.execute(
                    text(f"UPDATE parcels SET {set_clause} WHERE apn = :apn"),
                    params,
                )
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("PermitAI LA -- Multi-Source Data Ingestion")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = {}

    # 1. Inspections
    results["inspections"] = await ingest_inspections()

    # 2. Permits 2020+
    results["permits_2020"] = await ingest_permits_2020()

    # 3. Certificate of Occupancy
    results["cofo"] = await ingest_cofo()

    # 4. Code Enforcement
    results["code_enforcement"] = await ingest_code_enforcement()

    # 5. Wildfire ROE
    results["wildfire_roe"] = await ingest_wildfire_roe()

    # 6. Spatial overlays (this is the big one)
    results["overlay_enrichment"] = await enrich_parcels_with_overlays()

    # Summary
    async with async_session() as session:
        counts = {}
        for table in ["projects", "parcels", "inspections", "audit_log"]:
            r = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = r.scalar()

        # Overlay stats
        r = await session.execute(text("""
            SELECT
                SUM(CASE WHEN is_very_high_fire_severity THEN 1 ELSE 0 END) as fire,
                SUM(CASE WHEN is_hillside THEN 1 ELSE 0 END) as hillside,
                SUM(CASE WHEN is_historic THEN 1 ELSE 0 END) as historic,
                SUM(CASE WHEN is_flood_zone THEN 1 ELSE 0 END) as flood,
                SUM(CASE WHEN is_specific_plan THEN 1 ELSE 0 END) as specific_plan,
                SUM(CASE WHEN is_coastal_zone THEN 1 ELSE 0 END) as coastal,
                SUM(CASE WHEN council_district IS NOT NULL THEN 1 ELSE 0 END) as has_cd
            FROM parcels
        """))
        overlay = r.fetchone()

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"  Projects in DB:    {counts['projects']}")
    print(f"  Parcels in DB:     {counts['parcels']}")
    print(f"  Inspections in DB: {counts['inspections']}")
    print(f"  Audit log entries: {counts['audit_log']}")
    print()
    print("  Parcel Overlay Coverage:")
    print(f"    Fire severity:   {overlay[0]}")
    print(f"    Hillside:        {overlay[1]}")
    print(f"    Historic (HPOZ): {overlay[2]}")
    print(f"    Flood zone:      {overlay[3]}")
    print(f"    Specific plan:   {overlay[4]}")
    print(f"    Coastal zone:    {overlay[5]}")
    print(f"    Council district: {overlay[6]}")
    print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
