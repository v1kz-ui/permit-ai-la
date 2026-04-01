import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_AsGeoJSON, ST_Centroid, ST_Contains, ST_MakePoint
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.redis import get_redis
from app.middleware.auth import get_current_user
from app.models.clearance import Clearance
from app.models.parcel import Parcel
from app.models.project import Project
from app.schemas.common import ClearanceStatus, ProjectStatus
from app.schemas.parcel import ParcelResponse

router = APIRouter(prefix="/parcels", tags=["parcels"])

PARCEL_CACHE_TTL = 86400  # 24 hours

# NOTE: static routes (/map-data, /lookup/by-coordinates) are defined BEFORE
# the dynamic /{apn} route to prevent FastAPI matching "map-data" as an APN.

@router.get("/map-data")
async def get_map_data(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Return GeoJSON FeatureCollection of all active projects for the map.

    Each feature carries the project id, address, status, pathway, whether
    a bottleneck exists, and the parcel centroid as coordinates.  The
    dashboard map consumes this directly.

    Cached in Redis for 5 minutes so map loads are fast even with many projects.
    """
    CACHE_KEY = "map:project_features"
    CACHE_TTL = 300  # 5 minutes

    try:
        redis = await get_redis()
        cached = await redis.get(CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    # Join projects → parcels to get centroids, also flag bottleneck clearances
    stmt = (
        select(
            Project.id,
            Project.address,
            Project.status,
            Project.pathway,
            Project.predicted_total_days,
            Project.apn,
            ST_AsGeoJSON(ST_Centroid(Parcel.geom)).label("centroid_geojson"),
        )
        .outerjoin(Parcel, Parcel.apn == Project.apn)
        .where(Project.status.notin_([ProjectStatus.CLOSED, ProjectStatus.FINAL]))
    )
    rows = (await db.execute(stmt)).all()

    # Fetch bottleneck flags in one query
    bottleneck_stmt = select(Clearance.project_id).where(
        Clearance.is_bottleneck.is_(True),
        Clearance.status == ClearanceStatus.IN_REVIEW,
    )
    bottleneck_project_ids = {
        str(r[0]) for r in (await db.execute(bottleneck_stmt)).all()
    }

    features = []
    for row in rows:
        centroid = None
        if row.centroid_geojson:
            try:
                geom = json.loads(row.centroid_geojson)
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    centroid = {"lng": coords[0], "lat": coords[1]}
            except (json.JSONDecodeError, TypeError):
                pass

        # Skip projects with no resolvable location
        if centroid is None:
            continue

        project_id = str(row.id)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [centroid["lng"], centroid["lat"]],
            },
            "properties": {
                "id": project_id,
                "address": row.address,
                "status": row.status,
                "pathway": row.pathway,
                "predicted_total_days": row.predicted_total_days,
                "has_bottleneck": project_id in bottleneck_project_ids,
            },
        })

    result = {"type": "FeatureCollection", "features": features}

    try:
        redis = await get_redis()
        await redis.set(CACHE_KEY, json.dumps(result), ex=CACHE_TTL)
    except Exception:
        pass

    return result


@router.get("/lookup/by-coordinates", response_model=ParcelResponse)
async def lookup_parcel_by_coordinates(
    lat: float = Query(..., ge=33.0, le=35.0),
    lng: float = Query(..., ge=-119.0, le=-117.0),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    point = ST_MakePoint(lng, lat)
    result = await db.execute(
        select(Parcel).where(ST_Contains(Parcel.geom, point)).limit(1)
    )
    parcel = result.scalar_one_or_none()

    if parcel is None:
        raise HTTPException(status_code=404, detail="No parcel found at these coordinates")

    return ParcelResponse.model_validate(parcel)


# Dynamic route last — must come after all static paths to avoid swallowing them.
@router.get("/{apn}", response_model=ParcelResponse)
async def get_parcel_by_apn(
    apn: str,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Look up a parcel by APN. Results are cached in Redis for 24 hours."""
    cache_key = f"parcel:{apn}"
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return ParcelResponse.model_validate_json(cached)
    except Exception:
        pass

    result = await db.execute(select(Parcel).where(Parcel.apn == apn))
    parcel = result.scalar_one_or_none()

    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")

    response = ParcelResponse.model_validate(parcel)

    try:
        redis = await get_redis()
        await redis.set(cache_key, response.model_dump_json(), ex=PARCEL_CACHE_TTL)
    except Exception:
        pass

    return response
