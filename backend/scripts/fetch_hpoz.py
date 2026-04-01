"""
Investigate HPOZ data from LA City ArcGIS MapServer endpoints.
1. Check available layers on City_Planning_Department and Special_Areas MapServers
2. Try various WHERE clauses on candidate layers
3. If HPOZ polygons found, load into PostGIS and spatial join against parcels
"""

import requests
import json
import sys
import time

# ── helpers ──────────────────────────────────────────────────────────────────

def fetch_json(url, params=None, timeout=30):
    """GET JSON from URL, return parsed dict or None."""
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def list_layers(base_url):
    """Return list of (id, name, type) for all layers at a MapServer."""
    print(f"\n{'='*70}")
    print(f"Listing layers: {base_url}")
    print('='*70)
    data = fetch_json(base_url, params={"f": "json"})
    if not data:
        return []
    layers = data.get("layers", [])
    for l in layers:
        print(f"  Layer {l['id']:>3}: {l['name']:<50} ({l.get('type','?')})")
    return layers


def try_query_layer(base_url, layer_id, layer_name="", where="1=1",
                    result_type="count", out_fields="*", max_records=5):
    """Query a layer. Returns feature count or feature list."""
    url = f"{base_url}/{layer_id}/query"
    params = {
        "where": where,
        "f": "json",
        "returnGeometry": "false",
        "outFields": out_fields,
    }
    if result_type == "count":
        params["returnCountOnly"] = "true"
        params.pop("outFields", None)
    else:
        params["resultRecordCount"] = str(max_records)

    data = fetch_json(url, params=params)
    if data is None:
        return None

    if "error" in data:
        print(f"    Layer {layer_id} ({layer_name}): server error – {data['error'].get('message','?')}")
        return None

    if result_type == "count":
        cnt = data.get("count", 0)
        print(f"    Layer {layer_id} ({layer_name}): {cnt} features (where={where})")
        return cnt
    else:
        feats = data.get("features", [])
        print(f"    Layer {layer_id} ({layer_name}): got {len(feats)} sample features")
        if feats:
            # show field names + first record
            attrs = feats[0].get("attributes", {})
            print(f"      Fields: {list(attrs.keys())}")
            for f in feats[:3]:
                print(f"      -> {f.get('attributes',{})}")
        return feats


def search_hpoz_layers(base_url, layers):
    """Search for HPOZ-related layers by name keyword."""
    keywords = ["hpoz", "historic", "preservation", "overlay", "historic preservation"]
    hits = []
    for l in layers:
        name_lower = l["name"].lower()
        for kw in keywords:
            if kw in name_lower:
                hits.append(l)
                break
    if hits:
        print(f"\n  HPOZ-related layers found:")
        for h in hits:
            print(f"    Layer {h['id']}: {h['name']}")
    else:
        print(f"\n  No layers matched HPOZ keywords.")
    return hits


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    hpoz_layer_url = None  # will be set if we find the right layer
    hpoz_layer_id = None

    # ── 1. City Planning Department MapServer ────────────────────────────────
    cpd_base = "https://maps.lacity.org/lahub/rest/services/City_Planning_Department/MapServer"
    cpd_layers = list_layers(cpd_base)

    # Search by name
    cpd_hits = search_hpoz_layers(cpd_base, cpd_layers)

    # Also try the specific layers requested
    print(f"\n--- Probing specific layers on City_Planning_Department ---")
    probe_ids = [8, 9, 10, 11, 12]
    # Add any hits we found by name
    for h in cpd_hits:
        if h["id"] not in probe_ids:
            probe_ids.append(h["id"])

    for lid in probe_ids:
        lname = next((l["name"] for l in cpd_layers if l["id"] == lid), "?")
        for wh in ["1=1", "OBJECTID>0"]:
            cnt = try_query_layer(cpd_base, lid, lname, where=wh)
            if cnt and cnt > 0:
                # Get sample features
                try_query_layer(cpd_base, lid, lname, where=wh, result_type="sample")
                if "hpoz" in lname.lower() or "historic" in lname.lower() or "preservation" in lname.lower():
                    hpoz_layer_url = cpd_base
                    hpoz_layer_id = lid
                break  # no need to try second WHERE if first worked

    # ── 2. Special Areas MapServer ───────────────────────────────────────────
    sa_base = "https://maps.lacity.org/lahub/rest/services/Special_Areas/MapServer"
    sa_layers = list_layers(sa_base)

    sa_hits = search_hpoz_layers(sa_base, sa_layers)

    if sa_layers:
        print(f"\n--- Probing ALL layers on Special_Areas ---")
        for l in sa_layers:
            cnt = try_query_layer(sa_base, l["id"], l["name"], where="1=1")
            if cnt and cnt > 0:
                try_query_layer(sa_base, l["id"], l["name"], where="1=1", result_type="sample")
                if "hpoz" in l["name"].lower() or "historic" in l["name"].lower() or "preservation" in l["name"].lower():
                    hpoz_layer_url = sa_base
                    hpoz_layer_id = l["id"]

    # ── 3. Try additional known LA GIS endpoints ─────────────────────────────
    alt_bases = [
        "https://maps.lacity.org/lahub/rest/services/HPOZ/MapServer",
        "https://maps.lacity.org/lahub/rest/services/Zoning/MapServer",
        "https://maps.lacity.org/lahub/rest/services/Planning/MapServer",
    ]
    for ab in alt_bases:
        ab_layers = list_layers(ab)
        if ab_layers:
            ab_hits = search_hpoz_layers(ab, ab_layers)
            for l in ab_layers:
                cnt = try_query_layer(ab, l["id"], l["name"], where="1=1")
                if cnt and cnt > 0:
                    try_query_layer(ab, l["id"], l["name"], where="1=1", result_type="sample")
                    if "hpoz" in l["name"].lower() or "historic" in l["name"].lower():
                        hpoz_layer_url = ab
                        hpoz_layer_id = l["id"]

    # ── 4. Try LA Open Data / GeoHub ─────────────────────────────────────────
    print(f"\n{'='*70}")
    print("Trying LA GeoHub / Open Data endpoints for HPOZ")
    print('='*70)

    geohub_urls = [
        # LA GeoHub feature service for HPOZ
        "https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/HPOZ/FeatureServer",
        "https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/Historic_Preservation_Overlay_Zone/FeatureServer",
        "https://geohub.lacity.org/datasets/historic-preservation-overlay-zones-hpoz",
    ]
    for gu in geohub_urls:
        data = fetch_json(gu, params={"f": "json"})
        if data and "layers" in data:
            print(f"  Found service: {gu}")
            for l in data["layers"]:
                print(f"    Layer {l['id']}: {l['name']}")
                cnt = try_query_layer(gu, l["id"], l["name"], where="1=1")
                if cnt and cnt > 0:
                    try_query_layer(gu, l["id"], l["name"], where="1=1", result_type="sample")
                    hpoz_layer_url = gu
                    hpoz_layer_id = l["id"]
        elif data and "error" not in data:
            print(f"  Response from {gu}: no layers key. Keys: {list(data.keys())[:10]}")
        # else: error already printed

    # ── 5. Try ArcGIS Online search for HPOZ LA ─────────────────────────────
    print(f"\n{'='*70}")
    print("Searching ArcGIS Online for 'HPOZ Los Angeles'")
    print('='*70)
    search_url = "https://www.arcgis.com/sharing/rest/search"
    params = {
        "q": "HPOZ Los Angeles type:Feature Service",
        "f": "json",
        "num": 10,
    }
    data = fetch_json(search_url, params=params)
    if data and "results" in data:
        for r in data["results"]:
            print(f"  {r.get('title','')} | {r.get('url','')} | owner={r.get('owner','')}")
            svc_url = r.get("url", "")
            if svc_url and ("hpoz" in r.get("title","").lower() or "historic" in r.get("title","").lower()):
                svc_data = fetch_json(svc_url, params={"f": "json"})
                if svc_data and "layers" in svc_data:
                    for l in svc_data["layers"]:
                        print(f"    Layer {l['id']}: {l['name']}")
                        cnt = try_query_layer(svc_url, l["id"], l["name"], where="1=1")
                        if cnt and cnt > 0:
                            try_query_layer(svc_url, l["id"], l["name"], where="1=1", result_type="sample")
                            hpoz_layer_url = svc_url
                            hpoz_layer_id = l["id"]

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    if hpoz_layer_url and hpoz_layer_id is not None:
        print(f"  HPOZ layer FOUND: {hpoz_layer_url}/{hpoz_layer_id}")
        print("  Proceeding to download and load into PostGIS...")
        return hpoz_layer_url, hpoz_layer_id
    else:
        print("  No HPOZ polygon layer found with data across all endpoints tried.")
        print("  The data may be behind authentication or served as a different format.")
        return None, None


if __name__ == "__main__":
    url, lid = main()
    if url and lid is not None:
        # Write the found URL so the next script can pick it up
        with open("hpoz_source.json", "w") as f:
            json.dump({"url": url, "layer_id": lid}, f)
        print(f"\nSaved source info to hpoz_source.json")
