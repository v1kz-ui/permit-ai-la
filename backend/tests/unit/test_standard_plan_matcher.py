"""Tests for the standard plan matcher."""

import pytest

from app.ai.pathfinder.standard_plan_matcher import find_compatible_plans


class TestFindCompatiblePlans:
    def test_standard_r1_lot_matches(self):
        plans = find_compatible_plans(
            lot_width=55, lot_depth=120,
            zone_class="R1", proposed_sqft=2000,
            stories=2, is_hillside=False,
        )
        assert len(plans) > 0
        assert plans[0]["plan_id"].startswith("SP-R1")

    def test_large_lot_matches_type_c(self):
        plans = find_compatible_plans(
            lot_width=100, lot_depth=150,
            zone_class="R1", proposed_sqft=4000,
            stories=2, is_hillside=False,
        )
        assert any(p["plan_id"] == "SP-R1-C" for p in plans)

    def test_hillside_lot_matches_hillside_plan(self):
        plans = find_compatible_plans(
            lot_width=60, lot_depth=120,
            zone_class="R1", proposed_sqft=3000,
            stories=3, is_hillside=True,
        )
        assert any(p["plan_id"] == "SP-HILLSIDE-A" for p in plans)

    def test_oversized_project_no_match(self):
        plans = find_compatible_plans(
            lot_width=55, lot_depth=120,
            zone_class="R1", proposed_sqft=10000,
            stories=2, is_hillside=False,
        )
        assert len(plans) == 0

    def test_missing_dimensions_returns_empty(self):
        plans = find_compatible_plans(
            lot_width=None, lot_depth=None,
            zone_class="R1", proposed_sqft=2000,
            stories=2,
        )
        assert len(plans) == 0

    def test_compatibility_score_sorted(self):
        plans = find_compatible_plans(
            lot_width=55, lot_depth=125,
            zone_class="R1", proposed_sqft=2000,
            stories=2, is_hillside=False,
        )
        if len(plans) > 1:
            assert plans[0]["compatibility_score"] >= plans[1]["compatibility_score"]

    def test_days_saved_present(self):
        plans = find_compatible_plans(
            lot_width=55, lot_depth=120,
            zone_class="R1", proposed_sqft=2000,
            stories=2,
        )
        if plans:
            assert plans[0]["plan_check_days_saved"] > 0
