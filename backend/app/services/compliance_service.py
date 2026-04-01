"""Regulatory compliance checker for LA building permits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas.common import ClearanceDepartment, ClearanceStatus, ProjectPathway


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ComplianceResult:
    rule: str
    passed: bool
    message: str
    severity: str = "info"  # info | warning | blocking


@dataclass
class ComplianceReport:
    project_id: str
    pathway: str
    results: list[ComplianceResult] = field(default_factory=list)
    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)

    def add(self, result: ComplianceResult) -> None:
        self.results.append(result)
        if not result.passed:
            if result.severity == "blocking":
                self.blocking_issues.append(result.message)
                self.passed = False
            elif result.severity == "warning":
                self.warnings.append(result.message)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "pathway": self.pathway,
            "passed": self.passed,
            "results": [
                {
                    "rule": r.rule,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                }
                for r in self.results
            ],
            "warnings": self.warnings,
            "blocking_issues": self.blocking_issues,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _size_increase_pct(project: Any) -> float | None:
    """Return percentage size increase, or None if sqft data is missing."""
    original = getattr(project, "original_sqft", None)
    proposed = getattr(project, "proposed_sqft", None)
    if original and proposed and original > 0:
        return ((proposed - original) / original) * 100
    return None


def _clearance_names(project: Any) -> set[str]:
    """Extract set of clearance type strings from a project's clearances."""
    clearances = getattr(project, "clearances", []) or []
    return {c.clearance_type for c in clearances}


def _clearance_statuses(project: Any) -> dict[str, str]:
    """Map clearance_type -> status."""
    clearances = getattr(project, "clearances", []) or []
    return {c.clearance_type: c.status for c in clearances}


# ---------------------------------------------------------------------------
# Individual compliance checks
# ---------------------------------------------------------------------------

def check_eo1_compliance(project: Any) -> ComplianceResult:
    """Verify project meets EO1 requirements: <=10% size increase, same footprint,
    all required clearances present."""
    pct = _size_increase_pct(project)

    if pct is not None and pct > 10:
        return ComplianceResult(
            rule="eo1_size_limit",
            passed=False,
            message=f"EO1 requires <= 10% size increase; project has {pct:.1f}%",
            severity="blocking",
        )

    # Must stay on same footprint (proposed <= original)
    original = getattr(project, "original_sqft", None)
    proposed = getattr(project, "proposed_sqft", None)
    if original and proposed and proposed > original * 1.10:
        return ComplianceResult(
            rule="eo1_footprint",
            passed=False,
            message="EO1 requires same building footprint with <= 10% expansion",
            severity="blocking",
        )

    # Required clearances for EO1
    required = {"ladbs_plan_check"}
    if getattr(project, "is_coastal_zone", False):
        required.add("coastal_development_permit")
    if getattr(project, "is_hillside", False):
        required.add("grading_permit")

    present = _clearance_names(project)
    missing = required - present
    if missing:
        return ComplianceResult(
            rule="eo1_required_clearances",
            passed=False,
            message=f"EO1 missing required clearances: {', '.join(sorted(missing))}",
            severity="warning",
        )

    return ComplianceResult(
        rule="eo1_compliance",
        passed=True,
        message="Project meets EO1 requirements",
    )


def check_eo8_compliance(project: Any) -> ComplianceResult:
    """Verify EO8 requirements: <=50% size increase, expanded clearances."""
    pct = _size_increase_pct(project)

    if pct is not None and pct > 50:
        return ComplianceResult(
            rule="eo8_size_limit",
            passed=False,
            message=f"EO8 requires <= 50% size increase; project has {pct:.1f}%",
            severity="blocking",
        )

    # EO8 expanded clearances
    required = {"ladbs_plan_check", "design_review"}
    if getattr(project, "is_coastal_zone", False):
        required.add("coastal_development_permit")
    if getattr(project, "is_hillside", False):
        required.add("grading_permit")
    if getattr(project, "is_very_high_fire_severity", False):
        required.add("brush_clearance")

    present = _clearance_names(project)
    missing = required - present
    if missing:
        return ComplianceResult(
            rule="eo8_required_clearances",
            passed=False,
            message=f"EO8 missing required clearances: {', '.join(sorted(missing))}",
            severity="warning",
        )

    return ComplianceResult(
        rule="eo8_compliance",
        passed=True,
        message="Project meets EO8 requirements",
    )


def check_coastal_compliance(project: Any) -> ComplianceResult:
    """Verify coastal zone requirements met (CDP present)."""
    if not getattr(project, "is_coastal_zone", False):
        return ComplianceResult(
            rule="coastal_compliance",
            passed=True,
            message="Project is not in a coastal zone; check not applicable",
        )

    present = _clearance_names(project)
    if "coastal_development_permit" not in present:
        return ComplianceResult(
            rule="coastal_compliance",
            passed=False,
            message="Coastal zone project requires a Coastal Development Permit (CDP)",
            severity="blocking",
        )

    return ComplianceResult(
        rule="coastal_compliance",
        passed=True,
        message="Coastal Development Permit is present",
    )


def check_hillside_compliance(project: Any) -> ComplianceResult:
    """Verify hillside requirements met (grading permit present)."""
    if not getattr(project, "is_hillside", False):
        return ComplianceResult(
            rule="hillside_compliance",
            passed=True,
            message="Project is not in a hillside area; check not applicable",
        )

    present = _clearance_names(project)
    if "grading_permit" not in present:
        return ComplianceResult(
            rule="hillside_compliance",
            passed=False,
            message="Hillside project requires a grading permit",
            severity="blocking",
        )

    return ComplianceResult(
        rule="hillside_compliance",
        passed=True,
        message="Grading permit is present for hillside project",
    )


def full_compliance_check(project: Any) -> ComplianceReport:
    """Run all applicable compliance checks and return a ComplianceReport."""
    pathway = getattr(project, "pathway", ProjectPathway.UNKNOWN)
    report = ComplianceReport(
        project_id=str(getattr(project, "id", "")),
        pathway=str(pathway),
    )

    # Pathway-specific checks
    if pathway in (ProjectPathway.EO1_LIKE_FOR_LIKE, "eo1_like_for_like"):
        report.add(check_eo1_compliance(project))
    elif pathway in (ProjectPathway.EO8_EXPANDED, "eo8_expanded"):
        report.add(check_eo8_compliance(project))

    # Zone checks always apply
    report.add(check_coastal_compliance(project))
    report.add(check_hillside_compliance(project))

    return report


# ---------------------------------------------------------------------------
# Clearance sequence validation
# ---------------------------------------------------------------------------

# Department ordering: earlier departments must be cleared before later ones.
CLEARANCE_ORDER: list[str] = [
    "ladbs_plan_check",
    "dcp_planning_review",
    "design_review",
    "boe_engineering_review",
    "lafd_fire_review",
    "coastal_development_permit",
    "grading_permit",
    "brush_clearance",
    "ladwp_utility_clearance",
    "lasan_sewer_clearance",
    "lahd_housing_clearance",
    "la_county_health_clearance",
]

# Dependencies: key requires all values to be approved first.
CLEARANCE_DEPENDENCIES: dict[str, list[str]] = {
    "design_review": ["ladbs_plan_check"],
    "boe_engineering_review": ["ladbs_plan_check"],
    "lafd_fire_review": ["ladbs_plan_check"],
    "grading_permit": ["boe_engineering_review"],
    "ladwp_utility_clearance": ["ladbs_plan_check"],
    "lasan_sewer_clearance": ["boe_engineering_review"],
}


def validate_clearance_sequence(project: Any) -> ComplianceResult:
    """Verify that clearances are being completed in the correct dependency order."""
    statuses = _clearance_statuses(project)

    approved_statuses = {ClearanceStatus.APPROVED, "approved", ClearanceStatus.CONDITIONAL, "conditional"}
    violations: list[str] = []

    for clearance_type, deps in CLEARANCE_DEPENDENCIES.items():
        if clearance_type not in statuses:
            continue
        current_status = statuses[clearance_type]
        if current_status in approved_statuses:
            # Check that all dependencies are also approved
            for dep in deps:
                dep_status = statuses.get(dep)
                if dep_status and dep_status not in approved_statuses:
                    violations.append(
                        f"{clearance_type} is approved but dependency {dep} is still '{dep_status}'"
                    )

    if violations:
        return ComplianceResult(
            rule="clearance_sequence",
            passed=False,
            message=f"Clearance sequence violations: {'; '.join(violations)}",
            severity="warning",
        )

    return ComplianceResult(
        rule="clearance_sequence",
        passed=True,
        message="Clearance sequence is valid",
    )


# ---------------------------------------------------------------------------
# Requirements listing
# ---------------------------------------------------------------------------

PATHWAY_REQUIREMENTS: dict[str, dict] = {
    "eo1_like_for_like": {
        "name": "Executive Order 1 - Like-for-Like",
        "max_size_increase_pct": 10,
        "required_clearances": ["ladbs_plan_check"],
        "conditional_clearances": {
            "coastal_development_permit": "Required if in coastal zone",
            "grading_permit": "Required if in hillside area",
            "brush_clearance": "Required if in Very High Fire Severity Zone",
        },
        "estimated_days": 45,
        "notes": "Same footprint rebuild with minor modifications.",
    },
    "eo8_expanded": {
        "name": "Executive Order 8 - Expanded",
        "max_size_increase_pct": 50,
        "required_clearances": ["ladbs_plan_check", "design_review"],
        "conditional_clearances": {
            "coastal_development_permit": "Required if in coastal zone",
            "grading_permit": "Required if in hillside area",
            "brush_clearance": "Required if in Very High Fire Severity Zone",
        },
        "estimated_days": 90,
        "notes": "Allows larger expansion with additional review.",
    },
    "standard": {
        "name": "Standard Permit",
        "max_size_increase_pct": None,
        "required_clearances": [
            "ladbs_plan_check",
            "dcp_planning_review",
            "design_review",
            "boe_engineering_review",
        ],
        "conditional_clearances": {
            "coastal_development_permit": "Required if in coastal zone",
            "grading_permit": "Required if in hillside area",
            "brush_clearance": "Required if in Very High Fire Severity Zone",
            "lafd_fire_review": "Required for multi-story or commercial",
        },
        "estimated_days": 180,
        "notes": "Full plan check and multi-department review.",
    },
}


def get_pathway_requirements(pathway: str) -> dict | None:
    """Return the requirements definition for a given pathway."""
    return PATHWAY_REQUIREMENTS.get(pathway)
