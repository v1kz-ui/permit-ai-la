"""Tests for the ZIMAS parcel loader and geometry conversion."""

import pytest
from app.ingestion.zimas_loader import _geojson_to_wkt, map_feature_to_row


class TestGeojsonToWkt:
    def test_point(self):
        geo = {"type": "Point", "coordinates": [-118.5, 34.05]}
        wkt = _geojson_to_wkt(geo)
        assert wkt == "SRID=4326;POINT(-118.5 34.05)"

    def test_polygon(self):
        geo = {
            "type": "Polygon",
            "coordinates": [[[-118.5, 34.0], [-118.4, 34.0], [-118.4, 34.1], [-118.5, 34.0]]],
        }
        wkt = _geojson_to_wkt(geo)
        assert wkt is not None
        assert wkt.startswith("SRID=4326;POLYGON")
        assert "-118.5 34.0" in wkt

    def test_multipolygon(self):
        geo = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-118.5, 34.0], [-118.4, 34.0], [-118.4, 34.1], [-118.5, 34.0]]],
                [[[-118.3, 34.0], [-118.2, 34.0], [-118.2, 34.1], [-118.3, 34.0]]],
            ],
        }
        wkt = _geojson_to_wkt(geo)
        assert wkt is not None
        assert wkt.startswith("SRID=4326;MULTIPOLYGON")

    def test_none_returns_none(self):
        assert _geojson_to_wkt(None) is None

    def test_empty_dict_returns_none(self):
        assert _geojson_to_wkt({}) is None

    def test_missing_coordinates_returns_none(self):
        assert _geojson_to_wkt({"type": "Point"}) is None


class TestMapFeatureToRow:
    def _base_feature(self, **overrides) -> dict:
        feat = {
            "APN": "4480-001-001",
            "SitusAddress": "1000 PALISADES DR, LOS ANGELES CA 90272",
            "ZoneClass": "R1",
            "GeneralPlanLandUse": "Low Density Residential",
            "HeightDistrict": "1",
            "CoastalZone": 0,
            "Hillside": 0,
            "VeryHighFireSeverity": 1,
            "FloodZone": 0,
            "GeologicalHazard": 0,
            "Historic": 0,
            "HPOZ": 0,
            "LotAreaSqFt": 7500.0,
            "LotWidth": 60.0,
            "LotDepth": 125.0,
            "CouncilDistrict": 11,
            "CommunityPlanArea": "Palisades",
            "_geometry": {
                "type": "Point",
                "coordinates": [-118.5, 34.05],
            },
        }
        feat.update(overrides)
        return feat

    def test_basic_mapping(self):
        row = map_feature_to_row(self._base_feature())
        assert row is not None
        assert row["apn"] == "4480-001-001"
        assert row["zone_class"] == "R1"
        assert row["is_very_high_fire_severity"] is True
        assert row["is_coastal_zone"] is False
        assert row["lot_width"] == 60.0
        assert row["council_district"] == 11

    def test_geometry_converted(self):
        row = map_feature_to_row(self._base_feature())
        assert row is not None
        assert "geom" in row
        assert "SRID=4326" in row["geom"]

    def test_missing_apn_returns_none(self):
        feat = self._base_feature()
        del feat["APN"]
        assert map_feature_to_row(feat) is None

    def test_missing_geometry_still_returns_row(self):
        feat = self._base_feature()
        del feat["_geometry"]
        row = map_feature_to_row(feat)
        assert row is not None
        assert "geom" not in row  # No geom key if no geometry

    def test_truthy_overlay_values(self):
        row = map_feature_to_row(self._base_feature(CoastalZone=1, Hillside="Yes"))
        assert row is not None
        assert row["is_coastal_zone"] is True
        assert row["is_hillside"] is True

    def test_apn_whitespace_normalised(self):
        row = map_feature_to_row(self._base_feature(APN="4480 001 001"))
        assert row is not None
        assert " " not in row["apn"]

    def test_altadena_feature(self):
        feat = self._base_feature(
            APN="5840-012-003",
            CommunityPlanArea="Altadena",
            CouncilDistrict=None,
        )
        row = map_feature_to_row(feat)
        assert row is not None
        assert row["community_plan_area"] == "Altadena"
        assert row["council_district"] is None
