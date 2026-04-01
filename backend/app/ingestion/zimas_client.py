"""ZIMAS / LA GeoHub ArcGIS REST client for parcel data."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# LA City GeoHub parcel feature service (public)
GEOHUB_PARCELS_URL = (
    "https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services"
    "/LA_County_Parcels/FeatureServer/0/query"
)
DEFAULT_PAGE_SIZE = 1000
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2

# Fields we care about from the parcel layer.
_OUT_FIELDS = ",".join(
    [
        "APN",
        "SitusAddress",
        "ZoneClass",
        "GeneralPlanLandUse",
        "HeightDistrict",
        "SpecificPlan",
        "CommunityPlanArea",
        "CoastalZone",
        "Hillside",
        "VeryHighFireSeverity",
        "FloodZone",
        "GeologicalHazard",
        "Historic",
        "HPOZ",
        "LotAreaSqFt",
        "LotWidth",
        "LotDepth",
        "CouncilDistrict",
    ]
)


class ZimasClient:
    """Async client for querying LA City parcel data through the ArcGIS REST API."""

    def __init__(self, timeout: float = 60.0) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ZimasClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def fetch_parcels_bulk(
        self,
        community_plan_area: str,
    ) -> list[dict[str, Any]]:
        """Fetch all parcels for a given Community Plan Area, paginating via
        ``resultOffset`` / ``resultRecordCount``.

        Returns a flat list of feature-attribute dicts.
        """
        all_features: list[dict[str, Any]] = []
        offset = 0

        while True:
            params = self._build_query_params(
                where=f"CommunityPlanArea='{community_plan_area}'",
                offset=offset,
            )
            data = await self._request_with_retry(params)
            if data is None:
                break

            features = self._extract_features(data)
            all_features.extend(features)

            logger.info(
                "zimas.page_fetched",
                community_plan_area=community_plan_area,
                offset=offset,
                page_size=len(features),
                total_so_far=len(all_features),
            )

            # ArcGIS signals "no more pages" by returning fewer records or
            # setting ``exceededTransferLimit`` to false.
            exceeded = data.get("exceededTransferLimit", False)
            if len(features) < DEFAULT_PAGE_SIZE and not exceeded:
                break
            offset += DEFAULT_PAGE_SIZE

        return all_features

    async def fetch_parcel_by_apn(self, apn: str) -> dict[str, Any] | None:
        """Look up a single parcel by its Assessor Parcel Number (APN)."""
        params = self._build_query_params(where=f"APN='{apn}'", offset=0)
        data = await self._request_with_retry(params)
        if data is None:
            return None
        features = self._extract_features(data)
        return features[0] if features else None

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _build_query_params(self, where: str, offset: int) -> dict[str, str]:
        return {
            "where": where,
            "outFields": _OUT_FIELDS,
            "outSR": "4326",
            "f": "geojson",
            "resultRecordCount": str(DEFAULT_PAGE_SIZE),
            "resultOffset": str(offset),
            "returnGeometry": "true",
        }

    @staticmethod
    def _extract_features(data: dict) -> list[dict[str, Any]]:
        """Parse GeoJSON FeatureCollection and return attribute dicts with geometry."""
        features: list[dict[str, Any]] = []
        for feature in data.get("features", []):
            props = dict(feature.get("properties", {}))
            geometry = feature.get("geometry")
            if geometry:
                props["_geometry"] = geometry
            features.append(props)
        return features

    async def _request_with_retry(self, params: dict[str, str]) -> dict | None:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.get(GEOHUB_PARCELS_URL, params=params)
                if response.status_code == 200:
                    payload = response.json()
                    # ArcGIS sometimes returns 200 with an error body.
                    if "error" in payload:
                        logger.error(
                            "zimas.arcgis_error",
                            error=payload["error"],
                            attempt=attempt,
                        )
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(BACKOFF_BASE_SECONDS ** attempt)
                            continue
                        return None
                    return payload

                logger.warning(
                    "zimas.http_error",
                    status=response.status_code,
                    attempt=attempt,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE_SECONDS ** attempt)
                    continue
                return None

            except httpx.HTTPError as exc:
                logger.warning("zimas.request_error", error=str(exc), attempt=attempt)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE_SECONDS ** attempt)
                    continue
                return None

        return None
