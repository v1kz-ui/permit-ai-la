"""PathfinderAI Rules Engine - Determines permit pathway from parcel data and rebuild scope.

This is the deterministic layer. It evaluates versioned JSON rules and has absolute
veto power over any AI-generated recommendation. Claude API is used only for edge
cases that fall outside the rule definitions.
"""

import json
from pathlib import Path

import structlog

logger = structlog.get_logger()

RULES_DIR = Path(__file__).parent.parent.parent.parent.parent / "rules"


def load_rule(rule_id: str) -> dict:
    rule_path = RULES_DIR / f"{rule_id}.json"
    if not rule_path.exists():
        raise FileNotFoundError(f"Rule file not found: {rule_path}")
    with open(rule_path) as f:
        return json.load(f)


def evaluate_eo1_eligibility(parcel_data: dict, rebuild_scope: dict) -> dict:
    """Evaluate whether a project qualifies for EO1 like-for-like rebuild."""
    rule = load_rule("eo1_like_for_like")
    result = {
        "eligible": True,
        "pathway": "eo1_like_for_like",
        "reasons": [],
        "required_clearances": list(rule["still_required"]),
        "estimated_days": rule["estimated_timeline_days"]["standard"],
    }

    constraints = rule["eligibility"]["constraints"]

    # Check square footage increase
    original = rebuild_scope.get("original_sqft", 0)
    proposed = rebuild_scope.get("proposed_sqft", 0)
    if original > 0 and proposed > 0:
        increase_pct = ((proposed - original) / original) * 100
        if increase_pct > constraints["max_sqft_increase_pct"]:
            result["eligible"] = False
            result["reasons"].append(
                f"Proposed size exceeds {constraints['max_sqft_increase_pct']}% "
                f"increase limit ({increase_pct:.1f}% requested)"
            )

    # Check conditional requirements
    for cond in rule["conditional_requirements"]:
        if parcel_data.get(cond["condition"], False):
            result["required_clearances"].append(cond["requires"])

    # Adjust timeline estimate
    is_coastal = parcel_data.get("is_coastal_zone", False)
    is_hillside = parcel_data.get("is_hillside", False)
    if is_coastal and is_hillside:
        result["estimated_days"] = rule["estimated_timeline_days"]["with_both"]
    elif is_coastal:
        result["estimated_days"] = rule["estimated_timeline_days"]["with_coastal"]
    elif is_hillside:
        result["estimated_days"] = rule["estimated_timeline_days"]["with_hillside"]

    return result


def evaluate_eo8_eligibility(parcel_data: dict, rebuild_scope: dict) -> dict:
    """Evaluate whether a project qualifies for EO8 expanded rebuild."""
    rule = load_rule("eo8_expanded")
    result = {
        "eligible": True,
        "pathway": "eo8_expanded",
        "reasons": [],
        "required_clearances": list(rule["still_required"]),
        "estimated_days": rule["estimated_timeline_days"]["standard"],
    }

    constraints = rule["eligibility"]["constraints"]

    original = rebuild_scope.get("original_sqft", 0)
    proposed = rebuild_scope.get("proposed_sqft", 0)
    if original > 0 and proposed > 0:
        increase_pct = ((proposed - original) / original) * 100
        if increase_pct > constraints["max_sqft_increase_pct"]:
            result["eligible"] = False
            result["reasons"].append(
                f"Proposed size exceeds {constraints['max_sqft_increase_pct']}% "
                f"increase limit ({increase_pct:.1f}% requested)"
            )

    for cond in rule["conditional_requirements"]:
        condition = cond["condition"]
        if condition.startswith("sqft_increase"):
            if original > 0 and proposed > 0:
                increase_pct = ((proposed - original) / original) * 100
                if increase_pct > 20:
                    result["required_clearances"].append(cond["requires"])
        elif parcel_data.get(condition, False):
            result["required_clearances"].append(cond["requires"])

    is_coastal = parcel_data.get("is_coastal_zone", False)
    is_hillside = parcel_data.get("is_hillside", False)
    if is_coastal and is_hillside:
        result["estimated_days"] = rule["estimated_timeline_days"]["with_both"]
    elif is_coastal:
        result["estimated_days"] = rule["estimated_timeline_days"]["with_coastal"]
    elif is_hillside:
        result["estimated_days"] = rule["estimated_timeline_days"]["with_hillside"]

    return result


def determine_pathway(parcel_data: dict, rebuild_scope: dict) -> dict:
    """Determine the best permit pathway for a rebuild project.

    Evaluation order: EO1 (fastest) -> EO8 (intermediate) -> Standard (fallback).
    """
    # Try EO1 first
    eo1 = evaluate_eo1_eligibility(parcel_data, rebuild_scope)
    if eo1["eligible"]:
        return eo1

    # Try EO8
    eo8 = evaluate_eo8_eligibility(parcel_data, rebuild_scope)
    if eo8["eligible"]:
        return eo8

    # Fallback to standard
    return {
        "eligible": True,
        "pathway": "standard",
        "reasons": eo1["reasons"] + eo8["reasons"],
        "required_clearances": [
            "building_permit", "zoning_clearance", "fire_life_safety",
            "sewer_connection", "water_service", "lid_compliance",
            "plan_check_standard", "design_review",
        ],
        "estimated_days": 180,
    }
