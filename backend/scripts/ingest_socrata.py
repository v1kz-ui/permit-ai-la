"""Ingest additional Socrata datasets: inspections, permits 2020+, CofO, code enforcement.

Usage:
    cd backend
    python scripts/ingest_socrata.py
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

DATABASE_URL = "postgresql+asyncpg://permitai:permitai@localhost:5432/permitai"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

FIRE_ZIPS = ["90272", "90049", "90402", "91001"]


async def socrata_fetch(client, url, where_clause, order=":id", limit=50000):
    """Paginated Socrata fetch."""
    all_data = []
    offset = 0
    page = 1000
    while len(all_data) < limit:
        params = {"$where": where_clause, "$order": order, "$limit": str(page), "$offset": str(offset)}
        try:
            r = await client.get(url, params=params)
            if r.status_code != 200:
                print(f"    HTTP {r.status_code} at offset {offset}")
                break
            data = r.json()
            if not data:
                break
            all_data.extend(data)
            if len(data) < page:
                break
            offset += page
        except Exception as e:
            print(f"    Error at offset {offset}: {e}")
            break
    return all_data


async def ingest_inspections():
    """LADBS Building Inspections -> inspections table."""
    print("\n[1/4] LADBS Building Inspections...")
    url = "https://data.lacity.org/resource/9w5z-rg2h.json"

    # Get permit numbers from our projects
    async with async_session() as session:
        result = await session.execute(
            text("SELECT id, ladbs_permit_number FROM projects WHERE ladbs_permit_number IS NOT NULL")
        )
        permit_map = {row[1]: str(row[0]) for row in result.fetchall()}
    print(f"  {len(permit_map)} project permit numbers to match against")

    all_records = []
    async with httpx.AsyncClient(timeout=60) as client:
        # Fetch recent inspections (can't filter by zip on this dataset, so grab recent ones)
        records = await socrata_fetch(
            client, url,
            where_clause="inspection_date > '2023-01-01'",
            order="inspection_date DESC",
            limit=50000,
        )
        all_records = records
    print(f"  Fetched {len(all_records)} inspection records")

    # Match to our projects
    inserted = 0
    errors = 0
    seen = set()

    for rec in all_records:
        permit = rec.get("permit", "").strip()
        if not permit or permit not in permit_map:
            continue

        # Deduplicate by permit + inspection type + date
        insp_type = rec.get("inspection", "General")
        insp_date_raw = rec.get("inspection_date", "")
        dedup_key = f"{permit}:{insp_type}:{insp_date_raw}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        project_id = permit_map[permit]
        result_raw = (rec.get("inspection_result") or "").strip()

        status_map = {
            "Approved": "passed",
            "Correction Notice Issued": "failed",
            "Not Ready for Inspection": "failed",
            "No Access": "cancelled",
            "Partial Inspection": "scheduled",
            "Inspector Cancel": "cancelled",
        }
        status = status_map.get(result_raw, "scheduled")

        insp_date = None
        if insp_date_raw:
            try:
                insp_date = datetime.fromisoformat(insp_date_raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        row = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "inspection_type": insp_type[:100],
            "status": status,
            "scheduled_date": insp_date,
            "completed_date": insp_date if status in ("passed", "failed") else None,
            "inspector_name": None,
            "notes": result_raw[:500] if result_raw else None,
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("""INSERT INTO inspections (id, project_id, inspection_type, status,
                                scheduled_date, completed_date, inspector_name, notes, created_at, updated_at)
                                VALUES (:id, :project_id, :inspection_type, :status,
                                :scheduled_date, :completed_date, :inspector_name, :notes, NOW(), NOW())"""),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"    Insert error: {str(e)[:150]}")

    print(f"  Matched & inserted: {inserted}, Errors: {errors}")
    return inserted


async def ingest_permits_2020():
    """Permits Issued 2020+ -> enrich projects with zone/valuation/work desc."""
    print("\n[2/4] Permits Issued 2020+ (newer dataset)...")
    url = "https://data.lacity.org/resource/pi9x-tg5x.json"

    all_records = []
    async with httpx.AsyncClient(timeout=60) as client:
        for zc in FIRE_ZIPS:
            records = await socrata_fetch(client, url, where_clause=f"zip_code='{zc}'", order="issue_date DESC", limit=20000)
            all_records.extend(records)
            print(f"  [{zc}] {len(records)} permits")
    print(f"  Total: {len(all_records)}")

    # Enrich existing projects
    updated = 0
    new_inserted = 0
    errors = 0
    default_owner = str(uuid.uuid5(uuid.NAMESPACE_DNS, "system@permitai.la"))

    for rec in all_records:
        permit_nbr = rec.get("permit_nbr", "").strip()
        if not permit_nbr:
            continue

        work_desc = (rec.get("work_desc") or "")[:500]
        zone = rec.get("zone", "")
        valuation = rec.get("valuation")

        async with async_session() as session:
            try:
                async with session.begin():
                    # Try to update existing project
                    result = await session.execute(
                        text("""UPDATE projects SET
                                ai_reasoning = COALESCE(ai_reasoning, '') ||
                                    CASE WHEN ai_reasoning IS NULL OR ai_reasoning = '' THEN '' ELSE E'\n' END ||
                                    :info,
                                updated_at = NOW()
                             WHERE ladbs_permit_number = :pn RETURNING id"""),
                        {"pn": permit_nbr, "info": f"Zone: {zone} | Work: {work_desc}"},
                    )
                    if result.scalar():
                        updated += 1
                    else:
                        # New permit not in our DB yet - insert it
                        address = rec.get("primary_address", "Unknown")
                        status_raw = (rec.get("status_desc") or "").lower()
                        status = "intake"
                        if "issued" in status_raw:
                            status = "issued"
                        elif "approved" in status_raw or "ready" in status_raw:
                            status = "approved"
                        elif "plan check" in status_raw or "review" in status_raw:
                            status = "in_review"
                        elif "final" in status_raw or "cofo" in status_raw:
                            status = "final"

                        await session.execute(
                            text("""INSERT INTO projects (id, address, apn, owner_id, ladbs_permit_number,
                                    status, is_coastal_zone, is_very_high_fire_severity, created_at, updated_at)
                                    VALUES (:id, :addr, :apn, :owner, :pn, :status, :coastal, :fire, NOW(), NOW())
                                    ON CONFLICT (ladbs_permit_number) DO NOTHING"""),
                            {
                                "id": str(uuid.uuid4()),
                                "addr": f"{address}, Los Angeles, CA {rec.get('zip_code', '')}",
                                "apn": rec.get("apn"),
                                "owner": default_owner,
                                "pn": permit_nbr,
                                "status": status,
                                "coastal": rec.get("zip_code") == "90272",
                                "fire": rec.get("zip_code") in ("90272", "91001"),
                            },
                        )
                        new_inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"    Error: {str(e)[:150]}")

    print(f"  Updated: {updated}, New inserts: {new_inserted}, Errors: {errors}")
    return updated + new_inserted


async def ingest_cofo():
    """Certificate of Occupancy records."""
    print("\n[3/4] Certificate of Occupancy...")
    url = "https://data.lacity.org/resource/3f9m-afei.json"

    all_records = []
    async with httpx.AsyncClient(timeout=60) as client:
        for zc in FIRE_ZIPS:
            records = await socrata_fetch(client, url, where_clause=f"zip_code='{zc}'", order="cofo_issue_date DESC", limit=10000)
            all_records.extend(records)
            print(f"  [{zc}] {len(records)} CofO records")
    print(f"  Total: {len(all_records)}")

    # Store in audit_log for tracking
    inserted = 0
    errors = 0

    for rec in all_records:
        cofo_num = rec.get("cofo_number", "")
        if not cofo_num:
            continue

        parts = [rec.get("address_start", ""), rec.get("address_fraction", ""),
                 rec.get("street_direction", ""), rec.get("street_name", ""), rec.get("street_suffix", "")]
        address = " ".join(p for p in parts if p).strip()

        row = {
            "id": str(uuid.uuid4()),
            "table_name": "certificate_of_occupancy",
            "record_id": cofo_num,
            "action": rec.get("latest_status", "issued"),
            "new_value": json.dumps({
                "cofo_number": cofo_num,
                "issue_date": rec.get("cofo_issue_date"),
                "status": rec.get("latest_status"),
                "address": address,
                "zip": rec.get("zip_code"),
                "work_description": (rec.get("work_description") or "")[:300],
                "zone": rec.get("zone"),
                "census_tract": rec.get("census_tract"),
            }),
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("INSERT INTO audit_log (id, table_name, record_id, action, new_value, created_at) VALUES (:id, :table_name, :record_id, :action, CAST(:new_value AS jsonb), NOW())"),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    Error: {str(e)[:150]}")

    print(f"  Stored: {inserted} CofO audit records, Errors: {errors}")
    return inserted


async def ingest_code_enforcement():
    """Code enforcement cases."""
    print("\n[4/4] Code Enforcement Cases...")
    url = "https://data.lacity.org/resource/u82d-eh7z.json"

    all_records = []
    async with httpx.AsyncClient(timeout=60) as client:
        for zc in FIRE_ZIPS:
            records = await socrata_fetch(client, url, where_clause=f"zip='{zc}'", order="apno DESC", limit=10000)
            all_records.extend(records)
            print(f"  [{zc}] {len(records)} cases")
    print(f"  Total: {len(all_records)}")

    inserted = 0
    errors = 0

    for rec in all_records:
        case_num = rec.get("apno", "")
        if not case_num:
            continue

        address = " ".join(filter(None, [
            rec.get("stno"), rec.get("predir"), rec.get("stname"),
            rec.get("suffix"), rec.get("sufdir"),
        ])).strip()

        row = {
            "id": str(uuid.uuid4()),
            "table_name": "code_enforcement",
            "record_id": case_num,
            "action": rec.get("aptype", "case"),
            "new_value": json.dumps({
                "address": address,
                "zip": rec.get("zip"),
                "case_number": case_num,
                "case_type": rec.get("apname"),
                "status": rec.get("stat"),
            }),
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("""INSERT INTO audit_log (id, table_name, record_id, action, new_value, created_at)
                                VALUES (:id, :table_name, :record_id, :action, CAST(:new_value AS jsonb), NOW())"""),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    Error: {str(e)[:150]}")

    print(f"  Stored: {inserted} enforcement records, Errors: {errors}")
    return inserted


async def ingest_wildfire_roe():
    """Wildfire Recovery Right-of-Entry parcels from ArcGIS."""
    print("\n[BONUS] Wildfire Recovery ROE Parcels...")
    url = "https://maps.lacity.org/lahub/rest/services/WildfireRecovery/MapServer/1/query"

    all_features = []
    async with httpx.AsyncClient(timeout=60) as client:
        offset = 0
        while True:
            params = {"where": "1=1", "outFields": "*", "f": "json",
                      "resultRecordCount": "1000", "resultOffset": str(offset), "returnGeometry": "false"}
            try:
                r = await client.get(url, params=params)
                data = r.json()
                if "error" in data:
                    print(f"  Error: {data['error'].get('message', '?')}")
                    break
                features = data.get("features", [])
                all_features.extend(features)
                print(f"  Page {offset // 1000 + 1}: {len(features)} (total: {len(all_features)})")
                if len(features) < 1000:
                    break
                offset += 1000
            except Exception as e:
                print(f"  Error: {e}")
                break

    print(f"  Total ROE parcels: {len(all_features)}")

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
                "phase2_status": attrs.get("Phase_2_Status"),
                "erosion_control": attrs.get("Erosion_Control"),
            }),
        }

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text("""INSERT INTO audit_log (id, table_name, record_id, action, new_value, created_at)
                                VALUES (:id, :table_name, :record_id, :action, CAST(:new_value AS jsonb), NOW())"""),
                        row,
                    )
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    Error: {str(e)[:150]}")

    print(f"  Stored: {inserted} ROE records, Errors: {errors}")
    return inserted


async def main():
    print("=" * 60)
    print("PermitAI LA -- Socrata + ArcGIS Multi-Source Ingestion")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    r1 = await ingest_inspections()
    r2 = await ingest_permits_2020()
    r3 = await ingest_cofo()
    r4 = await ingest_code_enforcement()
    r5 = await ingest_wildfire_roe()

    # Final counts
    async with async_session() as session:
        for table in ["projects", "parcels", "inspections", "audit_log", "users"]:
            r = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            print(f"  {table}: {r.scalar()}")

        # Audit log breakdown
        r = await session.execute(text(
            "SELECT table_name, COUNT(*) FROM audit_log GROUP BY table_name ORDER BY COUNT(*) DESC"
        ))
        print("\n  Audit log breakdown:")
        for row in r.fetchall():
            print(f"    {row[0]}: {row[1]}")

    print("\n" + "=" * 60)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
