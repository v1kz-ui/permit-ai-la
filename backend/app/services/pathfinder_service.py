"""PathfinderAI Orchestration Service.

Combines the rules engine, Claude AI reasoning, standard plan matching,
bottleneck prediction, and conflict detection into a single pipeline.

Called when a project is created or when a user requests pathway analysis.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pathfinder.claude_reasoner import reason_about_pathway
from app.ai.pathfinder.rules_engine import determine_pathway
from app.ai.pathfinder.standard_plan_matcher import find_compatible_plans
from app.ai.predictor.bottleneck_model import predict_clearance_days, predict_project_timeline
from app.models.clearance import Clearance
from app.models.parcel import Parcel
from app.models.project import Project
from app.schemas.common import ClearanceDepartment, ClearanceStatus
from app.services.clearance_service import auto_generate_clearances, get_clearances_for_project
from app.services.conflict_service import detect_conflicts

logger = structlog.get_logger()

# Maps clearance type strings from rules to (department, display_name)
CLEARANCE_TYPE_MAP: dict[str, tuple[ClearanceDepartment, str]] = {
    "building_permit": (ClearanceDepartment.LADBS, "Building Permit"),
    "zoning_clearance": (ClearanceDepartment.DCP, "Zoning Clearance"),
    "fire_life_safety": (ClearanceDepartment.LAFD, "Fire/Life Safety Review"),
    "sewer_connection": (ClearanceDepartment.BOE, "Sewer Connection Clearance"),
    "water_service": (ClearanceDepartment.LADWP, "Water Service Clearance"),
    "lid_compliance": (ClearanceDepartment.LASAN, "LID Stormwater Compliance"),
    "plan_check_standard": (ClearanceDepartment.LADBS, "Standard Plan Check"),
    "design_review": (ClearanceDepartment.DCP, "Design Review"),
    "coastal_development_permit": (ClearanceDepartment.DCP, "Coastal Development Permit"),
    "grading_permit": (ClearanceDepartment.LADBS, "Grading Permit"),
    "brush_clearance": (ClearanceDepartment.LAFD, "Brush Clearance Verification"),
    "fire_flow": (ClearanceDepartment.LAFD, "Fire Flow/Hydrant Adequacy"),
    "historic_review": (ClearanceDepartment.DCP, "Historic Preservation Review"),
    "hpoz_review": (ClearanceDepartment.DCP, "HPOZ Board Review"),
    "specific_plan_compliance": (ClearanceDepartment.DCP, "Specific Plan Compliance"),
    "geotechnical_review": (ClearanceDepartment.LA_COUNTY, "Geotechnical Review"),
    "haul_route": (ClearanceDepartment.BOE, "Haul Route Approval"),
}


async def analyze_project(
    session: AsyncSession,
    project: Project,
    parcel: Parcel | None,
) -> dict:
    """Run the full PathfinderAI pipeline on a project.

    1. Rules engine determines pathway
    2. Claude API reasons about edge cases (if ambiguity exists)
    3. Standard plan matcher finds compatible pre-approved plans
    4. Generate required clearances from pathway result
    5. Predict timeline and bottlenecks for each clearance
    6. Detect conflicts between clearances
    7. Update project with predictions

    Returns the complete analysis result.
    """
    # Build input data
    parcel_data = _parcel_to_dict(parcel) if parcel else {}
    rebuild_scope = {
        "original_sqft": project.original_sqft,
        "proposed_sqft": project.proposed_sqft,
        "stories": project.stories,
        "description": project.description,
    }

    # Step 1: Deterministic rules evaluation
    rules_result = determine_pathway(parcel_data, rebuild_scope)
    logger.info(
        "rules_engine_result",
        project_id=str(project.id),
        pathway=rules_result["pathway"],
        eligible=rules_result["eligible"],
    )

    # Step 2: AI reasoning for edge cases
    ambiguity = _detect_ambiguity(parcel_data, rebuild_scope, rules_result)
    ai_result = {"ai_recommendation": None, "confidence": 0.0}
    if ambiguity:
        ai_result = await reason_about_pathway(
            parcel_data, rebuild_scope, rules_result, ambiguity
        )

    # Step 3: Standard plan matching
    compatible_plans = []
    if parcel:
        compatible_plans = find_compatible_plans(
            lot_width=parcel.lot_width,
            lot_depth=parcel.lot_depth,
            zone_class=parcel.zone_class,
            proposed_sqft=project.proposed_sqft,
            stories=project.stories,
            is_hillside=parcel.is_hillside,
        )

    # Step 4: Generate clearances from pathway result
    clearance_types = rules_result.get("required_clearances", [])
    # Add any AI-recommended additional clearances
    if ai_result.get("additional_clearances"):
        for ac in ai_result["additional_clearances"]:
            if ac not in clearance_types:
                clearance_types.append(ac)

    # Create clearance records
    await _ensure_clearances(session, project.id, clearance_types)

    # Also run parcel-based auto-generation
    if parcel:
        await auto_generate_clearances(session, project.id, parcel)

    # Step 5: Predict timeline and bottlenecks
    clearances = await get_clearances_for_project(session, project.id)
    clearance_dicts = [
        {"department": c.department, "clearance_type": c.clearance_type}
        for c in clearances
    ]
    current_month = datetime.now(timezone.utc).month
    timeline = predict_project_timeline(clearance_dicts, parcel_data, month=current_month)

    # Update clearance predicted_days from timeline results
    for c, cd in zip(clearances, clearance_dicts):
        if "predicted_days" in cd:
            c.predicted_days = cd["predicted_days"]
            c.is_bottleneck = cd.get("is_bottleneck", False)

    # Step 6: Detect conflicts
    conflicts = await detect_conflicts(session, project.id)

    # Step 7: Update project with predictions
    project.pathway = rules_result["pathway"]
    project.status = "plan_check" if rules_result["pathway"] != "unknown" else "intake"
    project.predicted_pathway = ai_result.get("ai_recommendation") or rules_result["pathway"]
    project.pathway_confidence = ai_result.get("confidence", 0.95 if not ambiguity else 0.7)
    project.predicted_days_to_issue = timeline["total_predicted_days"]
    project.estimated_completion_days = timeline["total_predicted_days"]

    # Apply standard plan savings to timeline
    if compatible_plans:
        best_plan = compatible_plans[0]
        project.predicted_days_to_issue -= best_plan["plan_check_days_saved"]

    await session.flush()

    result = {
        "project_id": str(project.id),
        "pathway": rules_result["pathway"],
        "pathway_eligible": rules_result["eligible"],
        "pathway_reasons": rules_result.get("reasons", []),
        "required_clearances": clearance_types,
        "ai_analysis": {
            "recommendation": ai_result.get("ai_recommendation"),
            "confidence": ai_result.get("confidence", 0.0),
            "reasoning": ai_result.get("reasoning", ""),
            "risk_factors": ai_result.get("risk_factors", []),
            "rules_engine_vetoed": ai_result.get("rules_engine_vetoed", False),
        },
        "standard_plans": compatible_plans[:3],
        "timeline": timeline,
        "conflicts": conflicts,
        "estimated_days": project.predicted_days_to_issue,
    }

    logger.info(
        "pathfinder_analysis_complete",
        project_id=str(project.id),
        pathway=result["pathway"],
        estimated_days=result["estimated_days"],
        clearance_count=len(clearance_types),
        bottleneck_count=timeline["bottleneck_count"],
        conflict_count=len(conflicts),
    )

    return result


async def _ensure_clearances(
    session: AsyncSession,
    project_id: uuid.UUID,
    clearance_types: list[str],
) -> None:
    """Create clearance records for each required type, skipping duplicates."""
    existing = await get_clearances_for_project(session, project_id)
    existing_types = {c.clearance_type.lower() for c in existing}

    for ctype in clearance_types:
        if ctype.lower() in existing_types:
            continue

        dept, display_name = CLEARANCE_TYPE_MAP.get(
            ctype, (ClearanceDepartment.LADBS, ctype.replace("_", " ").title())
        )

        clearance = Clearance(
            project_id=project_id,
            department=dept,
            clearance_type=display_name,
            status=ClearanceStatus.NOT_STARTED,
        )
        session.add(clearance)
        existing_types.add(ctype.lower())

    await session.flush()


def _parcel_to_dict(parcel: Parcel) -> dict:
    """Convert a Parcel ORM model to a dict for rules engine consumption."""
    return {
        "apn": parcel.apn,
        "zone_class": parcel.zone_class,
        "general_plan_land_use": parcel.general_plan_land_use,
        "height_district": parcel.height_district,
        "specific_plan": parcel.specific_plan,
        "community_plan_area": parcel.community_plan_area,
        "is_coastal_zone": parcel.is_coastal_zone,
        "is_hillside": parcel.is_hillside,
        "is_very_high_fire_severity": parcel.is_very_high_fire_severity,
        "is_flood_zone": parcel.is_flood_zone,
        "is_geological_hazard": parcel.is_geological_hazard,
        "is_historic": parcel.is_historic,
        "has_hpoz": parcel.has_hpoz,
        "lot_area_sqft": parcel.lot_area_sqft,
        "lot_width": parcel.lot_width,
        "lot_depth": parcel.lot_depth,
        "council_district": parcel.council_district,
        "has_specific_plan": bool(parcel.specific_plan),
    }


def _detect_ambiguity(parcel_data: dict, rebuild_scope: dict, rules_result: dict) -> str | None:
    """Detect if the project has edge cases that warrant AI reasoning."""
    reasons = []

    # Multiple overlays = complex interactions
    overlay_count = sum(
        1 for key in ["is_coastal_zone", "is_hillside", "is_very_high_fire_severity",
                       "is_historic", "is_flood_zone", "is_geological_hazard"]
        if parcel_data.get(key, False)
    )
    if overlay_count >= 3:
        reasons.append(f"Project has {overlay_count} overlapping overlay zones requiring complex interaction analysis")

    # Close to EO threshold
    original = rebuild_scope.get("original_sqft") or 0
    proposed = rebuild_scope.get("proposed_sqft") or 0
    if original > 0 and proposed > 0:
        increase_pct = ((proposed - original) / original) * 100
        if 8 <= increase_pct <= 12:
            reasons.append(f"Project size increase ({increase_pct:.1f}%) is near the EO1 10% threshold boundary")
        elif 45 <= increase_pct <= 55:
            reasons.append(f"Project size increase ({increase_pct:.1f}%) is near the EO8 50% threshold boundary")

    # Specific plan area adds complexity
    if parcel_data.get("has_specific_plan"):
        reasons.append("Property is in a Specific Plan area with additional regulatory requirements")

    if reasons:
        return "; ".join(reasons)
    return None
