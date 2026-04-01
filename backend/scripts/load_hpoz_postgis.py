"""
Download HPOZ polygons from two sources, load into PostGIS, and
spatial-join against the parcels table to set has_hpoz = true.

Sources:
  1. City Planning Dept MapServer layer 10 (35 features, official)
  2. ArcGIS Online LADCP FeatureServer (41 features, CPA-intersected)

We use source #1 (official city endpoint) as the canonical HPOZ boundaries.
"""

import json
import sys
import requests
import psycopg2
from psycopg2.extras import execute_values

# ── config ──────────────────────────────────────────────────────────────────

DB_DSN = "postgresql://permitai:permitai@localhost:5432/permitai"

# Official City Planning Dept — 35 HPOZ district polygons
CPD_URL = (
    "https://maps.lacity.org/lahub/rest/services/"
    "City_Planning_Department/MapServer/10/query"
)

# ArcGIS Online LADCP — 41 features (some districts split by CPA)
AGOL_URL = (
    "https://services1.arcgis.com/tzwalEyxl2rpamKs/arcgis/rest/services/"
    "Historic_Preservation_Overlay_Zones_e214e/FeatureServer/0/query"
)


def fetch_all_features(query_url, out_sr=4326, batch_size=100):
    """Download all features with geometry from an ArcGIS REST endpoint."""
    all_features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": out_sr,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }
        r = requests.get(query_url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()

        features = data.get("features", [])
        if not features:
            break
        all_features.extend(features)
        print(f"  Fetched {len(all_features)} features so far...")

        # Check if there are more
        if len(features) < batch_size:
            break
        offset += batch_size

    return all_features


def create_hpoz_table(conn):
    """Create hpoz_zones staging table."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS hpoz_zones CASCADE;")
        cur.execute("""
            CREATE TABLE hpoz_zones (
                id SERIAL PRIMARY KEY,
                name TEXT,
                source TEXT,
                geom geometry(MultiPolygon, 4326)
            );
        """)
        cur.execute("""
            CREATE INDEX idx_hpoz_zones_geom ON hpoz_zones USING GIST (geom);
        """)
    conn.commit()
    print("Created hpoz_zones table with spatial index.")


def insert_features(conn, features, source_label):
    """Insert GeoJSON features into hpoz_zones."""
    inserted = 0
    with conn.cursor() as cur:
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry")
            if not geom:
                continue

            # Get name from various possible field names
            name = (
                props.get("NAME")
                or props.get("name")
                or props.get("Name")
                or "Unknown"
            )

            geom_json = json.dumps(geom)
            # Convert to multi if needed, and set SRID
            cur.execute("""
                INSERT INTO hpoz_zones (name, source, geom)
                VALUES (
                    %s,
                    %s,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                )
            """, (name, source_label, geom_json))
            inserted += 1

    conn.commit()
    print(f"  Inserted {inserted} HPOZ polygons from {source_label}.")
    return inserted


def spatial_join_parcels(conn):
    """Update parcels.has_hpoz based on spatial intersection with hpoz_zones."""
    with conn.cursor() as cur:
        # First, count parcels with geometry
        cur.execute("SELECT count(*) FROM parcels WHERE geom IS NOT NULL;")
        total = cur.fetchone()[0]
        print(f"\nParcels with geometry: {total}")

        # Add has_hpoz column if it doesn't exist
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='parcels' AND column_name='has_hpoz'
                ) THEN
                    ALTER TABLE parcels ADD COLUMN has_hpoz boolean DEFAULT false;
                END IF;
            END $$;
        """)
        conn.commit()

        # Also add hpoz_name column if missing
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='parcels' AND column_name='hpoz_name'
                ) THEN
                    ALTER TABLE parcels ADD COLUMN hpoz_name text;
                END IF;
            END $$;
        """)
        conn.commit()
        print("Ensured has_hpoz and hpoz_name columns exist.")

        # Reset all to false first
        cur.execute("UPDATE parcels SET has_hpoz = false, hpoz_name = NULL;")
        reset_count = cur.rowcount
        print(f"Reset has_hpoz to false for {reset_count} parcels.")

        # Set has_hpoz = true and hpoz_name for parcels that intersect HPOZ zones
        cur.execute("""
            UPDATE parcels p
            SET has_hpoz = true,
                hpoz_name = sub.names
            FROM (
                SELECT p2.apn, string_agg(DISTINCT h.name, ', ') as names
                FROM parcels p2
                JOIN hpoz_zones h ON ST_Intersects(p2.geom, h.geom)
                WHERE p2.geom IS NOT NULL
                GROUP BY p2.apn
            ) sub
            WHERE p.apn = sub.apn;
        """)
        updated = cur.rowcount
        print(f"Set has_hpoz = true for {updated} parcels.")

        # Show breakdown by HPOZ district
        cur.execute("""
            SELECT h.name, count(DISTINCT p.apn) as parcel_count
            FROM parcels p
            JOIN hpoz_zones h ON ST_Intersects(p.geom, h.geom)
            WHERE p.geom IS NOT NULL
            GROUP BY h.name
            ORDER BY parcel_count DESC;
        """)
        rows = cur.fetchall()
        if rows:
            print(f"\nParcels per HPOZ district:")
            for name, cnt in rows:
                print(f"  {name:<35} {cnt:>6}")
            print(f"  {'TOTAL':<35} {sum(r[1] for r in rows):>6}")

    conn.commit()
    return updated


def main():
    # ── 1. Download from official City Planning endpoint ────────────────────
    print("=" * 70)
    print("Downloading HPOZ polygons from City Planning Dept MapServer layer 10")
    print("=" * 70)
    cpd_features = fetch_all_features(CPD_URL)
    print(f"Downloaded {len(cpd_features)} features from City Planning Dept.\n")

    if not cpd_features:
        print("ERROR: No features downloaded from CPD. Trying ArcGIS Online...")
        print("\nDownloading from ArcGIS Online LADCP FeatureServer")
        cpd_features = fetch_all_features(AGOL_URL)
        print(f"Downloaded {len(cpd_features)} features from ArcGIS Online.\n")
        source_label = "agol_ladcp"
    else:
        source_label = "cpd_mapserver_10"

    if not cpd_features:
        print("FATAL: No HPOZ features could be downloaded from any source.")
        sys.exit(1)

    # Show what we got
    for f in cpd_features[:5]:
        props = f.get("properties", {})
        name = props.get("NAME") or props.get("name") or "?"
        geom_type = f.get("geometry", {}).get("type", "?")
        print(f"  {name} ({geom_type})")
    if len(cpd_features) > 5:
        print(f"  ... and {len(cpd_features) - 5} more")

    # ── 2. Load into PostGIS ────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("Loading into PostGIS")
    print("=" * 70)

    conn = psycopg2.connect(DB_DSN)
    try:
        create_hpoz_table(conn)
        insert_features(conn, cpd_features, source_label)

        # ── 3. Spatial join against parcels ─────────────────────────────────
        print(f"\n{'='*70}")
        print("Spatial join: parcels vs hpoz_zones")
        print("=" * 70)
        updated = spatial_join_parcels(conn)

        print(f"\nDone. {updated} parcels flagged as within HPOZ districts.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
