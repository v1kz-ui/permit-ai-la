"""Standard Plan Matcher - Matches lot dimensions to pre-approved plan sets.

LA has pre-approved standard plan sets for common lot configurations. If a rebuild
matches one of these, the plan check process is significantly faster because the
plans have already been reviewed and approved.
"""

import structlog

logger = structlog.get_logger()

# Pre-approved standard plan configurations
# Based on common LA residential lot patterns in Pacific Palisades / Altadena
STANDARD_PLANS = [
    {
        "plan_id": "SP-R1-A",
        "name": "Standard R1 Single Family - Type A",
        "zone_class": "R1",
        "min_lot_width": 50,
        "max_lot_width": 60,
        "min_lot_depth": 100,
        "max_lot_depth": 150,
        "max_sqft": 2400,
        "max_stories": 2,
        "max_height_ft": 33,
        "compatible_overlays": ["standard"],
        "plan_check_days_saved": 15,
    },
    {
        "plan_id": "SP-R1-B",
        "name": "Standard R1 Single Family - Type B",
        "zone_class": "R1",
        "min_lot_width": 60,
        "max_lot_width": 80,
        "min_lot_depth": 100,
        "max_lot_depth": 150,
        "max_sqft": 3200,
        "max_stories": 2,
        "max_height_ft": 33,
        "compatible_overlays": ["standard"],
        "plan_check_days_saved": 15,
    },
    {
        "plan_id": "SP-R1-C",
        "name": "Standard R1 Single Family - Large Lot",
        "zone_class": "R1",
        "min_lot_width": 80,
        "max_lot_width": 120,
        "min_lot_depth": 120,
        "max_lot_depth": 200,
        "max_sqft": 4800,
        "max_stories": 2,
        "max_height_ft": 33,
        "compatible_overlays": ["standard"],
        "plan_check_days_saved": 12,
    },
    {
        "plan_id": "SP-RE-A",
        "name": "Standard RE Single Family - Estate",
        "zone_class": "RE",
        "min_lot_width": 70,
        "max_lot_width": 150,
        "min_lot_depth": 150,
        "max_lot_depth": 300,
        "max_sqft": 6000,
        "max_stories": 2,
        "max_height_ft": 36,
        "compatible_overlays": ["standard"],
        "plan_check_days_saved": 10,
    },
    {
        "plan_id": "SP-HILLSIDE-A",
        "name": "Hillside Standard - Stepped Foundation",
        "zone_class": "R1",
        "min_lot_width": 50,
        "max_lot_width": 100,
        "min_lot_depth": 80,
        "max_lot_depth": 200,
        "max_sqft": 3500,
        "max_stories": 3,
        "max_height_ft": 36,
        "compatible_overlays": ["hillside"],
        "plan_check_days_saved": 8,
    },
]


def find_compatible_plans(
    lot_width: float | None,
    lot_depth: float | None,
    zone_class: str | None,
    proposed_sqft: float | None,
    stories: int | None,
    is_hillside: bool = False,
) -> list[dict]:
    """Find pre-approved standard plans compatible with the given lot and scope.

    Returns a list of matching plans sorted by plan_check_days_saved (most savings first).
    """
    if not lot_width or not lot_depth:
        logger.info("standard_plan_match_skipped", reason="missing lot dimensions")
        return []

    matches = []

    for plan in STANDARD_PLANS:
        # Check lot width
        if not (plan["min_lot_width"] <= lot_width <= plan["max_lot_width"]):
            continue
        # Check lot depth
        if not (plan["min_lot_depth"] <= lot_depth <= plan["max_lot_depth"]):
            continue
        # Check zone compatibility
        if zone_class and plan["zone_class"] != zone_class.upper()[:2]:
            continue
        # Check proposed size
        if proposed_sqft and proposed_sqft > plan["max_sqft"]:
            continue
        # Check stories
        if stories and stories > plan["max_stories"]:
            continue
        # Check overlay compatibility
        if is_hillside and "hillside" not in plan["compatible_overlays"]:
            continue
        if not is_hillside and "standard" not in plan["compatible_overlays"]:
            continue

        matches.append({
            "plan_id": plan["plan_id"],
            "name": plan["name"],
            "max_sqft": plan["max_sqft"],
            "max_stories": plan["max_stories"],
            "plan_check_days_saved": plan["plan_check_days_saved"],
            "compatibility_score": _compute_compatibility(plan, lot_width, lot_depth, proposed_sqft),
        })

    matches.sort(key=lambda m: (-m["compatibility_score"], -m["plan_check_days_saved"]))

    logger.info(
        "standard_plan_match_complete",
        lot_width=lot_width,
        lot_depth=lot_depth,
        zone=zone_class,
        matches_found=len(matches),
    )

    return matches


def _compute_compatibility(
    plan: dict,
    lot_width: float,
    lot_depth: float,
    proposed_sqft: float | None,
) -> float:
    """Score 0-1 indicating how well the lot fits the plan (1.0 = perfect center)."""
    width_range = plan["max_lot_width"] - plan["min_lot_width"]
    width_center = (plan["max_lot_width"] + plan["min_lot_width"]) / 2
    width_score = max(0, 1.0 - abs(lot_width - width_center) / (width_range / 2)) if width_range > 0 else 1.0

    depth_range = plan["max_lot_depth"] - plan["min_lot_depth"]
    depth_center = (plan["max_lot_depth"] + plan["min_lot_depth"]) / 2
    depth_score = max(0, 1.0 - abs(lot_depth - depth_center) / (depth_range / 2)) if depth_range > 0 else 1.0

    sqft_score = 1.0
    if proposed_sqft and plan["max_sqft"] > 0:
        sqft_score = max(0, 1.0 - (proposed_sqft / plan["max_sqft"]))

    return round((width_score * 0.35 + depth_score * 0.35 + sqft_score * 0.3), 3)
