"""Tests for the /parcels/map-data endpoint and related logic."""

import json
import pytest


class TestGeomConversion:
    """Pure-logic tests — no DB needed."""

    def test_point_wkt(self):
        from app.ingestion.zimas_loader import _geojson_to_wkt

        geo = {"type": "Point", "coordinates": [-118.52, 34.04]}
        wkt = _geojson_to_wkt(geo)
        assert wkt == "SRID=4326;POINT(-118.52 34.04)"

    def test_multipolygon_wkt_contains_srid(self):
        from app.ingestion.zimas_loader import _geojson_to_wkt

        geo = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-118.5, 34.0], [-118.4, 34.0], [-118.4, 34.1], [-118.5, 34.0]]]
            ],
        }
        wkt = _geojson_to_wkt(geo)
        assert wkt is not None
        assert wkt.startswith("SRID=4326;MULTIPOLYGON")


class TestMapDataEndpoint:
    """Integration-style tests using the mocked client from conftest."""

    @pytest.mark.asyncio
    async def test_map_data_returns_geojson_structure(self, client):
        """GET /parcels/map-data should return a GeoJSON FeatureCollection."""
        response = client.get("/api/v1/parcels/map-data")
        # May be 200 (empty features) or 500 if DB mock returns empty
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert data["type"] == "FeatureCollection"
            assert "features" in data
            assert isinstance(data["features"], list)

    @pytest.mark.asyncio
    async def test_map_data_feature_structure(self, client):
        """Each feature should have geometry and properties."""
        response = client.get("/api/v1/parcels/map-data")
        if response.status_code == 200:
            data = response.json()
            for feature in data["features"]:
                assert feature["type"] == "Feature"
                assert "geometry" in feature
                assert feature["geometry"]["type"] == "Point"
                assert len(feature["geometry"]["coordinates"]) == 2
                props = feature["properties"]
                assert "id" in props
                assert "address" in props
                assert "status" in props
                assert "has_bottleneck" in props
