"""PathfinderAI API endpoints.

Provides AI-powered permit pathway analysis, timeline predictions,
conflict detection, and standard plan matching.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.parcel import Parcel
from app.models.project import Project
from app.services.pathfinder_service import analyze_project

router = APIRouter(prefix="/pathfinder", tags=["pathfinder"])


class PathfinderAnalysisResponse(BaseModel):
    project_id: str
    pathway: str
    pathway_eligible: bool
    pathway_reasons: list[str]
    required_clearances: list[str]
    ai_analysis: dict
    standard_plans: list[dict]
    timeline: dict
    conflicts: list[dict]
    estimated_days: int | None


class QuickAnalysisRequest(BaseModel):
    address: str
    original_sqft: float | None = None
    proposed_sqft: float | None = None
    stories: int | None = None


class QuickAnalysisResponse(BaseModel):
    pathway: str
    eligible: bool
    reasons: list[str]
    required_clearances: list[str]
    estimated_days: int
    parcel_found: bool
    overlays: dict


@router.post("/analyze/{project_id}", response_model=PathfinderAnalysisResponse)
async def analyze_project_pathway(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Run full PathfinderAI analysis on a project.

    This triggers the complete pipeline:
    1. Rules engine evaluation
    2. Claude AI reasoning (for edge cases)
    3. Standard plan matching
    4. Clearance auto-generation
    5. Timeline and bottleneck prediction
    6. Conflict detection
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Look up parcel
    parcel = None
    if project.apn:
        parcel_result = await db.execute(select(Parcel).where(Parcel.apn == project.apn))
        parcel = parcel_result.scalar_one_or_none()

    analysis = await analyze_project(db, project, parcel)
    return analysis


@router.post("/quick-analysis", response_model=QuickAnalysisResponse)
async def quick_pathway_analysis(
    data: QuickAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Quick pathway analysis from address only -- no project creation required.

    Useful for homeowners to get an instant estimate before starting the
    formal application process.
    """
    from sqlalchemy import func

    from app.ai.pathfinder.rules_engine import determine_pathway

    # Try to find parcel
    parcel = None
    parcel_result = await db.execute(
        select(Parcel).where(func.lower(Parcel.address) == func.lower(data.address.strip())).limit(1)
    )
    parcel = parcel_result.scalar_one_or_none()

    parcel_data = {}
    overlays = {
        "coastal_zone": False,
        "hillside": False,
        "very_high_fire_severity": False,
        "historic": False,
        "flood_zone": False,
        "geological_hazard": False,
    }

    if parcel:
        parcel_data = {
            "is_coastal_zone": parcel.is_coastal_zone,
            "is_hillside": parcel.is_hillside,
            "is_very_high_fire_severity": parcel.is_very_high_fire_severity,
            "is_flood_zone": parcel.is_flood_zone,
            "is_geological_hazard": parcel.is_geological_hazard,
            "is_historic": parcel.is_historic,
            "has_hpoz": parcel.has_hpoz,
            "has_specific_plan": bool(parcel.specific_plan),
        }
        overlays = {
            "coastal_zone": parcel.is_coastal_zone,
            "hillside": parcel.is_hillside,
            "very_high_fire_severity": parcel.is_very_high_fire_severity,
            "historic": parcel.is_historic,
            "flood_zone": parcel.is_flood_zone,
            "geological_hazard": parcel.is_geological_hazard,
        }

    rebuild_scope = {
        "original_sqft": data.original_sqft,
        "proposed_sqft": data.proposed_sqft,
        "stories": data.stories,
    }

    result = determine_pathway(parcel_data, rebuild_scope)

    return QuickAnalysisResponse(
        pathway=result["pathway"],
        eligible=result["eligible"],
        reasons=result.get("reasons", []),
        required_clearances=result.get("required_clearances", []),
        estimated_days=result.get("estimated_days", 180),
        parcel_found=parcel is not None,
        overlays=overlays,
    )


@router.get("/conflicts/{project_id}")
async def get_project_conflicts(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Detect and return conflicts between clearance requirements."""
    from app.services.conflict_service import detect_conflicts

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    conflicts = await detect_conflicts(db, project_id)
    return {"project_id": str(project_id), "conflicts": conflicts, "count": len(conflicts)}


@router.get("/timeline/{project_id}")
async def get_project_timeline(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Get predicted timeline breakdown for a project."""
    from app.ai.predictor.bottleneck_model import predict_project_timeline
    from app.services.clearance_service import get_clearances_for_project

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get parcel data for overlay multipliers
    parcel_data = {}
    if project.apn:
        parcel_result = await db.execute(select(Parcel).where(Parcel.apn == project.apn))
        parcel = parcel_result.scalar_one_or_none()
        if parcel:
            parcel_data = {
                "is_coastal_zone": parcel.is_coastal_zone,
                "is_hillside": parcel.is_hillside,
                "is_very_high_fire_severity": parcel.is_very_high_fire_severity,
                "is_historic": parcel.is_historic,
                "is_flood_zone": parcel.is_flood_zone,
                "is_geological_hazard": parcel.is_geological_hazard,
            }

    clearances = await get_clearances_for_project(db, project_id)
    clearance_dicts = [
        {"department": c.department, "clearance_type": c.clearance_type}
        for c in clearances
    ]

    from datetime import datetime, timezone
    timeline = predict_project_timeline(clearance_dicts, parcel_data, month=datetime.now(timezone.utc).month)

    return {
        "project_id": str(project_id),
        "pathway": project.pathway,
        **timeline,
    }


class WhatIfRequest(BaseModel):
    """Scenario inputs for what-if analysis."""
    address: str
    original_sqft: float
    proposed_sqft: float
    stories: int = 1
    # Scenario overrides — omit to use parcel actuals
    override_coastal_zone: bool | None = None
    override_hillside: bool | None = None
    override_historic: bool | None = None
    override_fire_severity: bool | None = None


class WhatIfScenario(BaseModel):
    label: str
    proposed_sqft: float
    pathway: str
    eligible: bool
    estimated_days: int
    key_constraints: list[str]


class WhatIfResponse(BaseModel):
    address: str
    parcel_found: bool
    scenarios: list[WhatIfScenario]
    recommendation: str


@router.post("/what-if", response_model=WhatIfResponse)
async def what_if_analysis(
    data: WhatIfRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Run what-if scenario analysis across three rebuild scopes.

    Returns pathway eligibility and estimated timelines for:
    1. The current proposed plan
    2. EO1 like-for-like maximum (10% increase)
    3. EO8 expanded maximum (50% increase)
    """
    from sqlalchemy import func

    from app.ai.pathfinder.rules_engine import determine_pathway

    # Look up parcel by address
    parcel_result = await db.execute(
        select(Parcel).where(func.lower(Parcel.address) == func.lower(data.address.strip())).limit(1)
    )
    parcel = parcel_result.scalar_one_or_none()

    # Build base parcel_data
    parcel_data: dict = {}
    if parcel:
        parcel_data = {
            "is_coastal_zone": parcel.is_coastal_zone,
            "is_hillside": parcel.is_hillside,
            "is_very_high_fire_severity": parcel.is_very_high_fire_severity,
            "is_flood_zone": parcel.is_flood_zone,
            "is_geological_hazard": parcel.is_geological_hazard,
            "is_historic": parcel.is_historic,
            "has_hpoz": parcel.has_hpoz,
            "has_specific_plan": bool(parcel.specific_plan),
        }

    # Apply override flags when provided
    if data.override_coastal_zone is not None:
        parcel_data["is_coastal_zone"] = data.override_coastal_zone
    if data.override_hillside is not None:
        parcel_data["is_hillside"] = data.override_hillside
    if data.override_historic is not None:
        parcel_data["is_historic"] = data.override_historic
    if data.override_fire_severity is not None:
        parcel_data["is_very_high_fire_severity"] = data.override_fire_severity

    def _build_constraints(pd: dict) -> list[str]:
        constraints = []
        if pd.get("is_coastal_zone"):
            constraints.append("coastal_zone")
        if pd.get("is_hillside"):
            constraints.append("hillside")
        if pd.get("is_very_high_fire_severity"):
            constraints.append("very_high_fire_severity")
        if pd.get("is_historic") or pd.get("has_hpoz"):
            constraints.append("historic")
        if pd.get("is_flood_zone"):
            constraints.append("flood_zone")
        if pd.get("is_geological_hazard"):
            constraints.append("geological_hazard")
        return constraints

    def _run_scenario(label: str, scenario_sqft: float) -> WhatIfScenario:
        rebuild_scope = {
            "original_sqft": data.original_sqft,
            "proposed_sqft": scenario_sqft,
            "stories": data.stories,
        }
        result = determine_pathway(parcel_data, rebuild_scope)
        return WhatIfScenario(
            label=label,
            proposed_sqft=scenario_sqft,
            pathway=result["pathway"],
            eligible=result["eligible"],
            estimated_days=result.get("estimated_days", 180),
            key_constraints=_build_constraints(parcel_data),
        )

    scenarios = [
        _run_scenario("Current Plan", data.proposed_sqft),
        _run_scenario("EO1 Like-for-Like Max", data.original_sqft * 1.10),
        _run_scenario("EO8 Expanded Max", data.original_sqft * 1.50),
    ]

    # Build recommendation from results
    eligible_scenarios = [s for s in scenarios if s.eligible]
    if not eligible_scenarios:
        recommendation = (
            "No standard pathway appears eligible given the current overlays. "
            "Consider consulting with LADBS staff for a discretionary review."
        )
    else:
        fastest = min(eligible_scenarios, key=lambda s: s.estimated_days)
        if fastest.label == "Current Plan":
            recommendation = (
                f"Your current plan is already on the fastest eligible pathway "
                f"({fastest.pathway}, ~{fastest.estimated_days} days). No scope change needed."
            )
        else:
            recommendation = (
                f"'{fastest.label}' offers the best balance of speed and scope: "
                f"{fastest.pathway} pathway (~{fastest.estimated_days} days). "
                f"Consider adjusting your proposed square footage to {fastest.proposed_sqft:,.0f} sqft."
            )

    return WhatIfResponse(
        address=data.address,
        parcel_found=parcel is not None,
        scenarios=scenarios,
        recommendation=recommendation,
    )
