"""Enrich parcels with spatial overlay data using PostGIS spatial joins.

SAFE APPROACH: Instead of 462K individual API calls, this script:
1. Fetches entire overlay polygon layers (only ~468 polygons total)
2. Loads them into temporary PostGIS tables
3. Runs spatial joins in SQL to flag all 77K parcels at once

Overlay layers:
  - VHFHSZ (Very High Fire Hazard Severity Zones) - 14 polygons
  - Hillside Ordinance areas - 344 polygons
  - HPOZ (Historic Preservation Overlay Zones) - 35 polygons
  - Specific Plan areas - 60 polygons
  - Council Districts - 15 polygons
  - FEMA Flood Zones (bbox query) - variable

Usage:
    cd backend
    python scripts/enrich_overlays.py
"""
from __future__ import annotations
import asyncio
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://permitai:permitai@localhost:5432/permitai"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

OVERLAY_LAYERS = [
    {
        "name": "vhfhsz",
        "label": "Very High Fire Hazard Severity Zones",
        "url": "https://maps.lacity.org/lahub/rest/services/Special_Areas/MapServer/11/query",
        "parcel_column": "is_very_high_fire_severity",
        "parcel_value": True,
    },
    {
        "name": "hillside",
        "label": "Hillside Ordinance",
        "url": "https://maps.lacity.org/lahub/rest/services/Special_Areas/MapServer/6/query",
        "parcel_column": "is_hillside",
        "parcel_value": True,
    },
    {
        "name": "hpoz",
        "label": "Historic Preservation Overlay Zones",
        "url": "https://maps.lacity.org/lahub/rest/services/City_Planning_Department/MapServer/10/query",
        "parcel_column": "is_historic",
        "parcel_value": True,
    },
    {
        "name": "specific_plan",
        "label": "Specific Plan Areas",
        "url": "https://maps.lacity.org/lahub/rest/services/City_Planning_Department/MapServer/19/query",
        "parcel_column": "is_specific_plan",
        "parcel_value": True,
        "name_field": "NAME",  # Also capture the plan name
    },
    {
        "name": "council_district",
        "label": "Council Districts",
        "url": "https://maps.lacity.org/lahub/rest/services/Boundaries/MapServer/13/query",
        "parcel_column": "council_district",
        "parcel_value": None,  # Use District attribute instead
        "district_field": "District",
    },
]

# FEMA bbox covers our fire areas
FEMA_BBOXES = [
    {"name": "Palisades/Brentwood", "bbox": "-118.58,34.00,-118.44,34.08"},
    {"name": "Altadena", "bbox": "-118.18,34.16,-118.10,34.22"},
]
FEMA_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"


def rings_to_wkt(rings: list) -> str | None:
    """Convert ArcGIS rings to WKT MULTIPOLYGON."""
    if not rings:
        return None
    try:
        poly_parts = []
        for ring in rings:
            pts = ", ".join(f"{x} {y}" for x, y in ring)
            poly_parts.append(f"(({pts}))")
        return f"SRID=4326;MULTIPOLYGON({', '.join(poly_parts)})"
    except (IndexError, TypeError, ValueError):
        return None


async def fetch_layer_polygons(client: httpx.AsyncClient, url: str, label: str) -> list[dict]:
    """Fetch ALL polygons from an ArcGIS layer with geometry."""
    all_features = []
    offset = 0
    page_size = 200

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
            "resultRecordCount": str(page_size),
            "resultOffset": str(offset),
            "returnGeometry": "true",
            "outSR": "4326",
        }
        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code}")
                break
            data = resp.json()
            if "error" in data:
                print(f"    Error: {data['error'].get('message', '?')}")
                break
            features = data.get("features", [])
            all_features.extend(features)
            if len(features) < page_size:
                break
            offset += page_size
        except Exception as e:
            print(f"    Fetch error: {e}")
            break

    print(f"  {label}: {len(all_features)} polygons fetched")
    return all_features


async def fetch_fema_polygons(client: httpx.AsyncClient) -> list[dict]:
    """Fetch FEMA flood zone polygons for our fire areas."""
    all_features = []

    for area in FEMA_BBOXES:
        offset = 0
        page_size = 500
        while True:
            params = {
                "geometry": area["bbox"],
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF",
                "f": "json",
                "resultRecordCount": str(page_size),
                "resultOffset": str(offset),
                "returnGeometry": "true",
                "outSR": "4326",
            }
            try:
                resp = await client.get(FEMA_URL, params=params)
                data = resp.json()
                if "error" in data:
                    print(f"    FEMA error for {area['name']}: {data['error'].get('message', '?')}")
                    break
                features = data.get("features", [])
                # Only keep actual flood hazard areas
                flood_features = [
                    f for f in features
                    if f.get("attributes", {}).get("SFHA_TF") == "T"
                    or f.get("attributes", {}).get("FLD_ZONE", "") in ("A", "AE", "AO", "AH", "V", "VE")
                ]
                all_features.extend(flood_features)
                if len(features) < page_size:
                    break
                offset += page_size
            except Exception as e:
                print(f"    FEMA error: {e}")
                break

    print(f"  FEMA Flood Zones: {len(all_features)} hazard polygons fetched")
    return all_features


async def load_overlay_to_postgis(layer_name: str, features: list[dict], name_field: str | None = None,
                                   district_field: str | None = None):
    """Load overlay polygons into a temporary PostGIS table."""
    async with async_session() as session:
        async with session.begin():
            # Drop and create temp table
            await session.execute(text(f"DROP TABLE IF EXISTS overlay_{layer_name}"))
            await session.execute(text(f"""
                CREATE TABLE overlay_{layer_name} (
                    id SERIAL PRIMARY KEY,
                    geom geometry(Geometry, 4326),
                    attr_name VARCHAR(255),
                    attr_district INTEGER
                )
            """))

    loaded = 0
    for feat in features:
        geom = feat.get("geometry", {})
        rings = geom.get("rings")
        if not rings:
            continue

        wkt = rings_to_wkt(rings)
        if not wkt:
            continue

        attr_name = None
        attr_district = None
        attrs = feat.get("attributes", {})
        if name_field:
            attr_name = str(attrs.get(name_field, ""))[:255]
        if district_field:
            try:
                attr_district = int(attrs.get(district_field, 0))
            except (ValueError, TypeError):
                attr_district = 0

        async with async_session() as session:
            try:
                async with session.begin():
                    await session.execute(
                        text(f"""
                            INSERT INTO overlay_{layer_name} (geom, attr_name, attr_district)
                            VALUES (ST_GeomFromEWKT(:wkt), :name, :district)
                        """),
                        {"wkt": wkt, "name": attr_name, "district": attr_district},
                    )
                loaded += 1
            except Exception as e:
                if loaded < 3:
                    print(f"    Load error: {str(e)[:120]}")

    # Create spatial index
    async with async_session() as session:
        async with session.begin():
            await session.execute(text(
                f"CREATE INDEX IF NOT EXISTS idx_overlay_{layer_name}_geom "
                f"ON overlay_{layer_name} USING GIST (geom)"
            ))

    print(f"    Loaded {loaded}/{len(features)} polygons into overlay_{layer_name}")
    return loaded


async def run_spatial_join(layer_name: str, parcel_column: str, parcel_value,
                            district_field: str | None = None, name_field: str | None = None):
    """Run a PostGIS spatial join to update parcel flags."""
    async with async_session() as session:
        async with session.begin():
            if district_field:
                # Council district: set the district number
                result = await session.execute(text(f"""
                    UPDATE parcels p
                    SET council_district = o.attr_district, updated_at = NOW()
                    FROM overlay_{layer_name} o
                    WHERE ST_Intersects(p.geom, o.geom)
                    AND (p.council_district IS NULL OR p.council_district = 0)
                """))
                print(f"    >> Updated {result.rowcount} parcels with council_district")

            elif name_field:
                # Specific plan: set flag + name
                result = await session.execute(text(f"""
                    UPDATE parcels p
                    SET {parcel_column} = true,
                        specific_plan_name = o.attr_name,
                        updated_at = NOW()
                    FROM overlay_{layer_name} o
                    WHERE ST_Intersects(p.geom, o.geom)
                """))
                print(f"    >> Updated {result.rowcount} parcels with {parcel_column} + name")

            else:
                # Boolean flag
                result = await session.execute(text(f"""
                    UPDATE parcels p
                    SET {parcel_column} = true, updated_at = NOW()
                    FROM overlay_{layer_name} o
                    WHERE ST_Intersects(p.geom, o.geom)
                """))
                print(f"    >> Updated {result.rowcount} parcels with {parcel_column}=true")


async def main():
    start = time.time()
    print("=" * 60)
    print("PermitAI LA -- PostGIS Spatial Join Overlay Enrichment")
    print("=" * 60)

    # Step 1: Fetch all overlay polygons
    print("\nStep 1: Fetching overlay polygons from ArcGIS...")
    async with httpx.AsyncClient(timeout=60) as client:
        layer_data = {}
        for layer in OVERLAY_LAYERS:
            features = await fetch_layer_polygons(client, layer["url"], layer["label"])
            layer_data[layer["name"]] = features

        fema_features = await fetch_fema_polygons(client)

    # Step 2: Load into PostGIS temp tables
    print("\nStep 2: Loading polygons into PostGIS...")
    for layer in OVERLAY_LAYERS:
        features = layer_data[layer["name"]]
        if features:
            await load_overlay_to_postgis(
                layer["name"], features,
                name_field=layer.get("name_field"),
                district_field=layer.get("district_field"),
            )

    if fema_features:
        await load_overlay_to_postgis("fema_flood", fema_features)

    # Step 3: Run spatial joins
    print("\nStep 3: Running spatial joins against 77K parcels...")
    for layer in OVERLAY_LAYERS:
        name = layer["name"]
        print(f"\n  Joining: {layer['label']}...")
        await run_spatial_join(
            name,
            layer["parcel_column"],
            layer["parcel_value"],
            district_field=layer.get("district_field"),
            name_field=layer.get("name_field"),
        )

    if fema_features:
        print(f"\n  Joining: FEMA Flood Zones...")
        await run_spatial_join("fema_flood", "is_flood_zone", True)

    # Step 4: Cleanup temp tables
    print("\nStep 4: Cleanup...")
    async with async_session() as session:
        async with session.begin():
            for layer in OVERLAY_LAYERS:
                await session.execute(text(f"DROP TABLE IF EXISTS overlay_{layer['name']}"))
            await session.execute(text("DROP TABLE IF EXISTS overlay_fema_flood"))
    print("  Temp tables dropped")

    # Final stats
    async with async_session() as session:
        r = await session.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_very_high_fire_severity THEN 1 ELSE 0 END) as fire,
                SUM(CASE WHEN is_hillside THEN 1 ELSE 0 END) as hillside,
                SUM(CASE WHEN is_historic THEN 1 ELSE 0 END) as historic,
                SUM(CASE WHEN is_flood_zone THEN 1 ELSE 0 END) as flood,
                SUM(CASE WHEN is_specific_plan THEN 1 ELSE 0 END) as sp,
                SUM(CASE WHEN is_coastal_zone THEN 1 ELSE 0 END) as coastal,
                SUM(CASE WHEN council_district IS NOT NULL AND council_district > 0 THEN 1 ELSE 0 END) as cd
            FROM parcels
        """))
        row = r.fetchone()

        # Council district breakdown
        r2 = await session.execute(text("""
            SELECT council_district, COUNT(*) FROM parcels
            WHERE council_district IS NOT NULL AND council_district > 0
            GROUP BY council_district ORDER BY council_district
        """))
        cd_rows = r2.fetchall()

        # Specific plan breakdown
        r3 = await session.execute(text("""
            SELECT specific_plan_name, COUNT(*) FROM parcels
            WHERE is_specific_plan GROUP BY specific_plan_name ORDER BY COUNT(*) DESC LIMIT 10
        """))
        sp_rows = r3.fetchall()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"ENRICHMENT COMPLETE in {elapsed:.0f}s")
    print(f"{'='*60}")
    print(f"  Total parcels:         {row[0]:,}")
    print(f"  Fire severity (VHFHSZ): {row[1]:,}")
    print(f"  Hillside:              {row[2]:,}")
    print(f"  Historic (HPOZ):       {row[3]:,}")
    print(f"  Flood zone (FEMA):     {row[4]:,}")
    print(f"  Specific plan:         {row[5]:,}")
    print(f"  Coastal zone:          {row[6]:,}")
    print(f"  Council district:      {row[7]:,}")

    if cd_rows:
        print(f"\n  Council Districts:")
        for cd, cnt in cd_rows:
            print(f"    District {cd}: {cnt:,} parcels")

    if sp_rows:
        print(f"\n  Top Specific Plans:")
        for name, cnt in sp_rows:
            print(f"    {name}: {cnt:,}")

    print(f"{'='*60}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
