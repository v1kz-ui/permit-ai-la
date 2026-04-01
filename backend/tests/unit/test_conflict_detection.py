"""Tests for conflict detection service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.common import ClearanceDepartment, ClearanceStatus


def _make_clearance(department: str, clearance_type: str):
    """Create a mock clearance object."""
    c = MagicMock()
    c.id = uuid.uuid4()
    c.project_id = uuid.uuid4()
    c.department = department
    c.clearance_type = clearance_type
    c.status = ClearanceStatus.NOT_STARTED
    c.conflict_with_id = None
    c.conflict_description = None
    return c


class TestConflictRules:
    """Test that known conflict patterns are correctly defined."""

    def test_coastal_vs_fire_conflict_exists(self):
        from app.services.conflict_service import CONFLICT_RULES
        ids = [r["id"] for r in CONFLICT_RULES]
        assert "coastal_vs_fire" in ids

    def test_historic_vs_rebuild_conflict_exists(self):
        from app.services.conflict_service import CONFLICT_RULES
        ids = [r["id"] for r in CONFLICT_RULES]
        assert "historic_vs_rebuild" in ids

    def test_all_rules_have_required_fields(self):
        from app.services.conflict_service import CONFLICT_RULES
        for rule in CONFLICT_RULES:
            assert "id" in rule
            assert "dept_a" in rule
            assert "dept_b" in rule
            assert "description" in rule
            assert "severity" in rule
            assert "resolution" in rule
            assert rule["severity"] in ("low", "medium", "high")
