"""Tests for PathfinderAI rules engine."""

import pytest

from app.ai.pathfinder.rules_engine import (
    determine_pathway,
    evaluate_eo1_eligibility,
    evaluate_eo8_eligibility,
)


class TestEO1Eligibility:
    def test_like_for_like_eligible(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2100}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert result["eligible"] is True
        assert result["pathway"] == "eo1_like_for_like"
        assert result["estimated_days"] == 45

    def test_exceeds_10pct_ineligible(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2300}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert result["eligible"] is False
        assert "exceeds" in result["reasons"][0].lower()

    def test_exactly_10pct_eligible(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2200}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert result["eligible"] is True

    def test_coastal_adds_clearance_and_time(self):
        parcel = {"is_coastal_zone": True, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2000}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert result["eligible"] is True
        assert "coastal_development_permit" in result["required_clearances"]
        assert result["estimated_days"] == 90

    def test_hillside_adds_clearance_and_time(self):
        parcel = {"is_coastal_zone": False, "is_hillside": True}
        scope = {"original_sqft": 2000, "proposed_sqft": 2000}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert "grading_permit" in result["required_clearances"]
        assert result["estimated_days"] == 75

    def test_coastal_and_hillside_combined(self):
        parcel = {"is_coastal_zone": True, "is_hillside": True}
        scope = {"original_sqft": 2000, "proposed_sqft": 2000}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert result["estimated_days"] == 120

    def test_fire_severity_adds_brush_clearance(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False, "is_very_high_fire_severity": True}
        scope = {"original_sqft": 2000, "proposed_sqft": 2000}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert "brush_clearance" in result["required_clearances"]

    def test_no_sqft_data_still_eligible(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {}
        result = evaluate_eo1_eligibility(parcel, scope)
        assert result["eligible"] is True


class TestEO8Eligibility:
    def test_30pct_increase_eligible(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2600}
        result = evaluate_eo8_eligibility(parcel, scope)
        assert result["eligible"] is True
        assert result["pathway"] == "eo8_expanded"

    def test_exceeds_50pct_ineligible(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 3100}
        result = evaluate_eo8_eligibility(parcel, scope)
        assert result["eligible"] is False

    def test_25pct_triggers_design_review(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2500}
        result = evaluate_eo8_eligibility(parcel, scope)
        assert result["eligible"] is True
        assert "design_review" in result["required_clearances"]


class TestDeterminePathway:
    def test_small_increase_gets_eo1(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2100}
        result = determine_pathway(parcel, scope)
        assert result["pathway"] == "eo1_like_for_like"

    def test_medium_increase_gets_eo8(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 2400}
        result = determine_pathway(parcel, scope)
        assert result["pathway"] == "eo8_expanded"

    def test_large_increase_gets_standard(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {"original_sqft": 2000, "proposed_sqft": 3500}
        result = determine_pathway(parcel, scope)
        assert result["pathway"] == "standard"
        assert result["estimated_days"] == 180

    def test_no_sqft_defaults_to_eo1(self):
        parcel = {"is_coastal_zone": False, "is_hillside": False}
        scope = {}
        result = determine_pathway(parcel, scope)
        assert result["pathway"] == "eo1_like_for_like"
