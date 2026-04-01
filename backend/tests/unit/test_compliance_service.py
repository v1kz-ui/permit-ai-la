"""Tests for compliance_service."""

import pytest

from app.services.compliance_service import (
    check_coastal_compliance,
    check_eo1_compliance,
    check_eo8_compliance,
    check_hillside_compliance,
    validate_clearance_sequence,
)


class FakeClearance:
    def __init__(self, clearance_type: str, status: str = "not_started"):
        self.clearance_type = clearance_type
        self.status = status


class FakeProject:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "test-id")
        self.original_sqft = kwargs.get("original_sqft")
        self.proposed_sqft = kwargs.get("proposed_sqft")
        self.pathway = kwargs.get("pathway", "eo1_like_for_like")
        self.is_coastal_zone = kwargs.get("is_coastal_zone", False)
        self.is_hillside = kwargs.get("is_hillside", False)
        self.is_very_high_fire_severity = kwargs.get("is_very_high_fire_severity", False)
        self.clearances = kwargs.get("clearances", [])


class TestEO1Compliance:
    def test_eo1_compliance_passes_within_10_percent(self):
        project = FakeProject(
            original_sqft=2000,
            proposed_sqft=2200,
            clearances=[FakeClearance("ladbs_plan_check")],
        )
        result = check_eo1_compliance(project)
        assert result.passed is True

    def test_eo1_compliance_fails_over_10_percent(self):
        project = FakeProject(
            original_sqft=2000,
            proposed_sqft=2300,
        )
        result = check_eo1_compliance(project)
        assert result.passed is False
        assert result.severity == "blocking"
        assert "10%" in result.message


class TestEO8Compliance:
    def test_eo8_compliance_passes_within_50_percent(self):
        project = FakeProject(
            original_sqft=2000,
            proposed_sqft=3000,
            clearances=[
                FakeClearance("ladbs_plan_check"),
                FakeClearance("design_review"),
            ],
        )
        result = check_eo8_compliance(project)
        assert result.passed is True

    def test_eo8_compliance_fails_over_50_percent(self):
        project = FakeProject(
            original_sqft=2000,
            proposed_sqft=3100,
        )
        result = check_eo8_compliance(project)
        assert result.passed is False
        assert result.severity == "blocking"
        assert "50%" in result.message


class TestCoastalCompliance:
    def test_coastal_compliance_requires_cdp(self):
        project = FakeProject(is_coastal_zone=True, clearances=[])
        result = check_coastal_compliance(project)
        assert result.passed is False
        assert result.severity == "blocking"
        assert "Coastal Development Permit" in result.message

    def test_coastal_compliance_passes_with_cdp(self):
        project = FakeProject(
            is_coastal_zone=True,
            clearances=[FakeClearance("coastal_development_permit")],
        )
        result = check_coastal_compliance(project)
        assert result.passed is True

    def test_non_coastal_skips(self):
        project = FakeProject(is_coastal_zone=False)
        result = check_coastal_compliance(project)
        assert result.passed is True


class TestHillsideCompliance:
    def test_hillside_compliance_requires_grading(self):
        project = FakeProject(is_hillside=True, clearances=[])
        result = check_hillside_compliance(project)
        assert result.passed is False
        assert result.severity == "blocking"
        assert "grading permit" in result.message.lower()

    def test_hillside_compliance_passes_with_grading(self):
        project = FakeProject(
            is_hillside=True,
            clearances=[FakeClearance("grading_permit")],
        )
        result = check_hillside_compliance(project)
        assert result.passed is True


class TestClearanceSequence:
    def test_clearance_sequence_valid(self):
        project = FakeProject(
            clearances=[
                FakeClearance("ladbs_plan_check", status="approved"),
                FakeClearance("design_review", status="approved"),
            ]
        )
        result = validate_clearance_sequence(project)
        assert result.passed is True

    def test_clearance_sequence_invalid(self):
        # design_review approved but its dependency ladbs_plan_check is still in_review
        project = FakeProject(
            clearances=[
                FakeClearance("ladbs_plan_check", status="in_review"),
                FakeClearance("design_review", status="approved"),
            ]
        )
        result = validate_clearance_sequence(project)
        assert result.passed is False
        assert "design_review" in result.message
        assert "ladbs_plan_check" in result.message
