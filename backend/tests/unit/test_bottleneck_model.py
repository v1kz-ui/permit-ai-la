"""Tests for the bottleneck prediction model."""

import pytest

from app.ai.predictor.bottleneck_model import (
    BOTTLENECK_THRESHOLD_DAYS,
    predict_clearance_days,
    predict_project_timeline,
)


class TestPredictClearanceDays:
    def test_standard_department_prediction(self):
        result = predict_clearance_days("dcp", "zoning_clearance", {})
        assert result["predicted_days"] > 0
        assert result["method"] == "heuristic"
        assert 0 <= result["confidence"] <= 1

    def test_coastal_increases_days(self):
        base = predict_clearance_days("dcp", "coastal_development_permit", {})
        coastal = predict_clearance_days(
            "dcp", "coastal_development_permit",
            {"is_coastal_zone": True}
        )
        assert coastal["predicted_days"] >= base["predicted_days"]

    def test_multiple_overlays_stack(self):
        no_overlay = predict_clearance_days("ladbs", "building_permit", {})
        overlays = predict_clearance_days(
            "ladbs", "building_permit",
            {"is_coastal_zone": True, "is_hillside": True, "is_very_high_fire_severity": True}
        )
        assert overlays["predicted_days"] > no_overlay["predicted_days"]

    def test_bottleneck_flagging(self):
        result = predict_clearance_days(
            "dcp", "coastal_development_permit",
            {"is_coastal_zone": True, "is_hillside": True}
        )
        # Coastal + hillside should push this over the threshold
        assert result["is_bottleneck"] is True
        assert result["predicted_days"] > BOTTLENECK_THRESHOLD_DAYS

    def test_unknown_department_falls_back(self):
        result = predict_clearance_days("unknown_dept", "unknown_type", {})
        assert result["predicted_days"] > 0
        assert result["method"] == "heuristic"


class TestPredictProjectTimeline:
    def test_basic_timeline(self):
        clearances = [
            {"department": "ladbs", "clearance_type": "building_permit"},
            {"department": "dcp", "clearance_type": "zoning_clearance"},
            {"department": "boe", "clearance_type": "sewer_connection"},
        ]
        result = predict_project_timeline(clearances, {})
        assert result["total_predicted_days"] > 0
        assert result["critical_department"] is not None
        assert isinstance(result["bottlenecks"], list)

    def test_parallel_departments(self):
        # Two clearances in same department should be sequential
        same_dept = [
            {"department": "ladbs", "clearance_type": "building_permit"},
            {"department": "ladbs", "clearance_type": "grading_permit"},
        ]
        different_dept = [
            {"department": "ladbs", "clearance_type": "building_permit"},
            {"department": "dcp", "clearance_type": "zoning_clearance"},
        ]
        same_result = predict_project_timeline(same_dept, {})
        diff_result = predict_project_timeline(different_dept, {})
        # Same department should take longer (sequential)
        assert same_result["critical_path_days"] > diff_result["critical_path_days"]

    def test_empty_clearances(self):
        result = predict_project_timeline([], {})
        assert result["total_predicted_days"] == 8  # just overhead
        assert result["bottleneck_count"] == 0
