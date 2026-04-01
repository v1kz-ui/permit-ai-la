"""Clearance conflict detection service.

Detects when two department requirements contradict each other. For example,
one department may require vegetation removal while another requires tree preservation.
Uses rule-based pattern matching with NLP fallback for comment analysis.
"""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clearance import Clearance

logger = structlog.get_logger()

# Known conflict patterns between department requirements
CONFLICT_RULES: list[dict] = [
    {
        "id": "coastal_vs_fire",
        "dept_a": "dcp",
        "type_a_pattern": "coastal",
        "dept_b": "lafd",
        "type_b_pattern": "brush_clearance",
        "description": (
            "Coastal Zone restrictions may limit brush/vegetation clearing "
            "required by LAFD for fire safety. Coastal Act protections can "
            "conflict with fire hazard abatement requirements."
        ),
        "severity": "high",
        "resolution": (
            "Request joint DCP-LAFD review. Coastal Commission staff can "
            "issue an emergency exemption for fire safety brush clearance."
        ),
    },
    {
        "id": "historic_vs_rebuild",
        "dept_a": "dcp",
        "type_a_pattern": "historic",
        "dept_b": "ladbs",
        "type_b_pattern": "building_permit",
        "description": (
            "Historic preservation requirements may restrict modifications "
            "needed for current building code compliance. Original materials "
            "or design features may conflict with seismic or fire safety upgrades."
        ),
        "severity": "medium",
        "resolution": (
            "Request Secretary of Interior Standards review for fire-rebuild. "
            "EO1 provides exemptions for like-for-like rebuilds in HPOZ areas."
        ),
    },
    {
        "id": "hillside_vs_grading",
        "dept_a": "boe",
        "type_a_pattern": "drainage",
        "dept_b": "ladbs",
        "type_b_pattern": "grading",
        "description": (
            "BOE drainage requirements may conflict with LADBS grading "
            "limitations on hillside lots. Maximum grading quantity limits "
            "per LAMC 91.7006 may prevent required drainage improvements."
        ),
        "severity": "medium",
        "resolution": (
            "Submit combined grading and drainage plan. BOE and LADBS can "
            "conduct joint review to reconcile quantity limits with drainage needs."
        ),
    },
    {
        "id": "lid_vs_fire_access",
        "dept_a": "lasan",
        "type_a_pattern": "lid",
        "dept_b": "lafd",
        "type_b_pattern": "fire",
        "description": (
            "LID stormwater management features (bioswales, permeable paving) "
            "may conflict with LAFD fire apparatus access requirements for "
            "paved surfaces rated for heavy vehicle loads."
        ),
        "severity": "low",
        "resolution": (
            "Use reinforced permeable paving systems that meet both LID "
            "infiltration and LAFD load-bearing requirements."
        ),
    },
    {
        "id": "flood_vs_foundation",
        "dept_a": "boe",
        "type_a_pattern": "flood",
        "dept_b": "ladbs",
        "type_b_pattern": "building_permit",
        "description": (
            "Flood zone elevation requirements may conflict with hillside "
            "height restrictions or neighborhood compatibility standards."
        ),
        "severity": "medium",
        "resolution": (
            "Request FEMA Letter of Map Amendment (LOMA) if post-fire "
            "topography has changed. Alternatively, apply for height variance."
        ),
    },
]


async def detect_conflicts(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> list[dict]:
    """Scan all clearances for a project and detect potential conflicts.

    Returns a list of detected conflicts with descriptions and resolutions.
    """
    result = await session.execute(
        select(Clearance)
        .where(Clearance.project_id == project_id)
        .order_by(Clearance.department)
    )
    clearances = list(result.scalars().all())

    if len(clearances) < 2:
        return []

    detected = []

    for rule in CONFLICT_RULES:
        clearance_a = None
        clearance_b = None

        for c in clearances:
            dept = c.department.lower() if isinstance(c.department, str) else c.department.value.lower()
            ctype = c.clearance_type.lower()

            if dept == rule["dept_a"] and rule["type_a_pattern"] in ctype:
                clearance_a = c
            if dept == rule["dept_b"] and rule["type_b_pattern"] in ctype:
                clearance_b = c

        if clearance_a and clearance_b:
            # Both conflicting clearances exist on this project
            detected.append({
                "conflict_id": rule["id"],
                "clearance_a_id": str(clearance_a.id),
                "clearance_a": f"{clearance_a.department}: {clearance_a.clearance_type}",
                "clearance_b_id": str(clearance_b.id),
                "clearance_b": f"{clearance_b.department}: {clearance_b.clearance_type}",
                "description": rule["description"],
                "severity": rule["severity"],
                "resolution": rule["resolution"],
            })

            # Update clearance records with conflict references
            clearance_a.conflict_with_id = clearance_b.id
            clearance_a.conflict_description = rule["description"]
            clearance_b.conflict_with_id = clearance_a.id
            clearance_b.conflict_description = rule["description"]

    if detected:
        await session.flush()
        logger.info(
            "conflicts_detected",
            project_id=str(project_id),
            count=len(detected),
            conflict_ids=[d["conflict_id"] for d in detected],
        )

    return detected
