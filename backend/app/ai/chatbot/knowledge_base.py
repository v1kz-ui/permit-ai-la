"""LA Permit Knowledge Base for RAG-powered chatbot.

Stores regulatory knowledge about LA fire-rebuild permits as structured
documents with metadata. Used for retrieval-augmented generation.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class KnowledgeDocument:
    """A single knowledge-base entry with content and metadata."""

    id: str
    title: str
    content: str
    category: str
    source: str
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Permit knowledge corpus
# ---------------------------------------------------------------------------

PERMIT_KNOWLEDGE: list[KnowledgeDocument] = [
    # 1 - EO1 Like-for-Like eligibility
    KnowledgeDocument(
        id="eo1_eligibility",
        title="EO1 Like-for-Like – Eligibility Requirements",
        category="eligibility",
        source="Mayor's Executive Order 1 (2025)",
        tags=["EO1", "like-for-like", "eligibility", "size", "footprint", "zone"],
        content=(
            "Executive Order 1 (EO1) – Like-for-Like Rebuild:\n"
            "Eligibility criteria:\n"
            "- Structure must have been destroyed or substantially damaged in the 2025 LA wildfires.\n"
            "- Rebuild may be up to 110% of the original structure's square footage (i.e., up to 10% size increase).\n"
            "- New footprint must match the original footprint or be placed within the same buildable envelope.\n"
            "- Must remain in the same zoning designation as the original structure.\n"
            "- Cannot be used for a change of use (residential stays residential).\n"
            "- Owner must provide documentation proving original structure dimensions (assessor records, survey, or prior permit).\n"
            "- Properties in the Coastal Zone, Hillside areas, HPOZ, or other special overlay zones may have additional requirements even under EO1.\n"
            "- Project must comply with current California Building Code (CBC) for structural, energy, and accessibility provisions unless a specific waiver is granted.\n"
        ),
    ),
    # 2 - EO1 timeline and required docs
    KnowledgeDocument(
        id="eo1_timeline",
        title="EO1 Like-for-Like – Timeline and Required Documents",
        category="timeline",
        source="Mayor's Executive Order 1 (2025); LADBS Fire Rebuild Guidance",
        tags=["EO1", "like-for-like", "timeline", "documents", "plan check", "permit"],
        content=(
            "EO1 Like-for-Like Rebuild – Typical Timeline: ~45 to 120 days from application to permit issuance.\n\n"
            "Phase breakdown:\n"
            "- Application preparation & submittal: 1–2 weeks\n"
            "- LADBS plan check (expedited): 2–4 weeks (standard plans may reduce this to 1–2 weeks)\n"
            "- Clearances from other departments (BOE, LAFD, LADWP, LASAN): 2–6 weeks (can run in parallel)\n"
            "- Permit issuance after all clearances: 1–3 business days\n\n"
            "Required documents for EO1 application:\n"
            "1. Completed permit application (LADBS online portal or in person)\n"
            "2. Proof of original structure size: County Assessor records, prior permits, or a licensed surveyor's report\n"
            "3. Site plan showing property lines, existing/proposed footprint\n"
            "4. Architectural plans (floor plan, elevations, sections) – signed by licensed architect or engineer\n"
            "5. Title report or proof of ownership\n"
            "6. Proof of fire damage (fire department incident report or LADBS damage assessment)\n"
            "7. HOA approval letter (if applicable)\n"
            "8. Soils/geotechnical report (required for hillside parcels or if prior soils report not on record)\n"
        ),
    ),
    # 3 - EO8 Expanded eligibility
    KnowledgeDocument(
        id="eo8_eligibility",
        title="EO8 Expanded Rebuild – Eligibility and Allowances",
        category="eligibility",
        source="Mayor's Executive Order 8 (2025)",
        tags=["EO8", "expanded", "eligibility", "150%", "footprint", "size increase"],
        content=(
            "Executive Order 8 (EO8) – Expanded Rebuild Pathway:\n"
            "Eligibility:\n"
            "- Structure destroyed or substantially damaged in the 2025 LA wildfires.\n"
            "- Allows rebuilding up to 150% of the original structure's square footage.\n"
            "- New footprint may differ from the original footprint (new placement on lot is allowed within setback and zoning rules).\n"
            "- Must remain in the same zone; no change of use permitted.\n"
            "- Owner must demonstrate original structure size via assessor or prior permit records.\n"
            "- EO8 is subject to full CEQA review if the project triggers any thresholds (e.g., demolition of protected trees, grading >1000 cy).\n"
            "- Coastal Zone properties: Coastal Development Permit (CDP) from CA Coastal Commission is still required.\n"
            "- Historic/HPOZ properties: Department of City Planning (DCP) review required; Mills Act status must be maintained.\n\n"
            "Key difference from EO1: EO8 allows more design flexibility (new footprint, up to 150% size) at the cost of a longer review timeline.\n"
        ),
    ),
    # 4 - EO8 timeline
    KnowledgeDocument(
        id="eo8_timeline",
        title="EO8 Expanded Rebuild – Timeline",
        category="timeline",
        source="Mayor's Executive Order 8 (2025); LADBS Fire Rebuild Guidance",
        tags=["EO8", "expanded", "timeline", "90 days", "180 days"],
        content=(
            "EO8 Expanded Rebuild – Typical Timeline: ~90 to 180 days from application to permit issuance.\n\n"
            "Phase breakdown:\n"
            "- Pre-application consultation with LADBS: 1–2 weeks (strongly recommended)\n"
            "- Application preparation & submittal: 2–4 weeks (more complex plans than EO1)\n"
            "- LADBS plan check: 4–8 weeks\n"
            "- Clearances (BOE, LAFD, LADWP, LASAN, and potentially DCP): 4–10 weeks (parallel)\n"
            "- Coastal Commission CDP review (if Coastal Zone): adds 30–60 days\n"
            "- Permit issuance: 1–5 business days after all clearances\n\n"
            "Tips to stay on the shorter end:\n"
            "- Submit complete plans on first attempt to avoid resubmittal cycles.\n"
            "- Hire a permit expediter familiar with LA fire-rebuild processes.\n"
            "- Request a concurrent review meeting with all clearance departments early.\n"
        ),
    ),
    # 5 - Standard permitting
    KnowledgeDocument(
        id="standard_permitting",
        title="Standard Permitting – When EO Thresholds Are Exceeded",
        category="process",
        source="LAMC Title 91 (Building Code); LADBS Standard Procedures",
        tags=["standard permit", "non-EO", "over 150%", "180 days", "full CEQA"],
        content=(
            "Standard Permitting (Non-Executive-Order Pathway):\n"
            "Applies when:\n"
            "- Proposed new structure exceeds 150% of the original structure's square footage, OR\n"
            "- Project involves a change of use, OR\n"
            "- Owner opts out of the EO pathways for any reason.\n\n"
            "Timeline: 180+ days (6 months or more); complex projects can take 12–18 months.\n\n"
            "Key additional requirements over EO pathways:\n"
            "- Full discretionary review by Department of City Planning (DCP) may be required.\n"
            "- CEQA environmental review is typically required.\n"
            "- Neighborhood Council notification may be required.\n"
            "- Design review boards (if in HPOZ or specific plan area).\n"
            "- Variance or Conditional Use Permit (CUP) if project exceeds zoning envelope.\n\n"
            "Recommendation: Unless the homeowner specifically needs a larger home, the EO1 or EO8 pathways are significantly faster and have fewer bureaucratic hurdles.\n"
        ),
    ),
    # 6 - Self-certification
    KnowledgeDocument(
        id="self_certification",
        title="Self-Certification – Architect-Stamped Plan Check Acceleration",
        category="process",
        source="LAMC Section 98.0402; LADBS Self-Certification Program",
        tags=["self-certification", "architect", "plan check", "expedite", "speed"],
        content=(
            "Self-Certification Program (LADBS):\n"
            "What it is: A licensed California architect or engineer 'self-certifies' that the plans comply with applicable codes, allowing LADBS to skip or abbreviate the plan check review.\n\n"
            "How it works:\n"
            "- Architect or engineer stamps and signs plans with a declaration of code compliance.\n"
            "- LADBS accepts the self-certification and issues the permit faster – typically cutting plan check time from 4–8 weeks to 1–2 weeks.\n"
            "- LADBS may still conduct a random audit review.\n"
            "- Architect/engineer bears legal responsibility for code compliance.\n\n"
            "Eligibility for self-certification:\n"
            "- Available for most residential R-1 and R-2 projects.\n"
            "- Not available for projects in certain Coastal Zone areas that require Coastal Commission approval first.\n"
            "- Architect must be registered with LADBS self-certification program.\n\n"
            "Benefit for fire-rebuild: Using self-certification under EO1 can reduce total permit timeline from 45–120 days to as few as 30–60 days.\n"
        ),
    ),
    # 7 - Coastal Zone
    KnowledgeDocument(
        id="coastal_zone",
        title="Coastal Zone – CDP Requirements for Fire Rebuilds",
        category="overlays",
        source="California Coastal Act (PRC §30000+); LA Local Coastal Program",
        tags=["coastal zone", "CDP", "coastal commission", "overlay", "30 days", "60 days"],
        content=(
            "Coastal Zone Requirements for Fire Rebuilds:\n"
            "If the property is within the California Coastal Zone:\n"
            "- A Coastal Development Permit (CDP) from the California Coastal Commission (or the City of LA's certified Local Coastal Program, if applicable) is required in addition to the regular building permit.\n"
            "- CDP adds approximately 30–60 days to the permit timeline for routine rebuilds.\n"
            "- Appealable areas and projects with new footprints may take longer (90–120+ days).\n\n"
            "Process:\n"
            "1. Submit CDP application to CA Coastal Commission or City of LA LCP office concurrently with LADBS application.\n"
            "2. Commission staff reviews for consistency with Coastal Act policies (visual access, public access, hazards, etc.).\n"
            "3. For like-for-like rebuilds under EO1 in non-appealable areas, an emergency CDP may be available (processed in ~10 business days).\n\n"
            "Key considerations:\n"
            "- Rebuilding in the same footprint is generally more favorable for Coastal Act review.\n"
            "- Expanding toward the beach or adding height may trigger more rigorous review.\n"
            "- Contact CA Coastal Commission's South Coast District office (Long Beach) for project-specific guidance.\n"
        ),
    ),
    # 8 - Hillside ordinance
    KnowledgeDocument(
        id="hillside_ordinance",
        title="Hillside Ordinance – Additional Requirements for Hillside Properties",
        category="overlays",
        source="LAMC Section 12.21-A.17; Hillside Area Construction Regulations",
        tags=["hillside", "soils report", "geotechnical", "haul route", "grading", "retaining wall"],
        content=(
            "Hillside Ordinance Requirements (LAMC §12.21-A.17):\n"
            "Properties in Hillside Areas (as designated on ZIMAS) require additional submittals and approvals:\n\n"
            "Required additional documents:\n"
            "1. Soils/Geotechnical Report: Must be prepared by a licensed geotechnical engineer. Report must address bearing capacity, expansive soils, slope stability, and liquefaction potential.\n"
            "2. Grading Plan: If more than 50 cubic yards of grading, a separate grading permit is required.\n"
            "3. Haul Route Approval: Bureau of Engineering (BOE) must approve the route for trucking debris and materials.\n"
            "4. Retaining wall calculations (if applicable).\n\n"
            "Timeline impact: Add 2–6 weeks for soils report preparation and BOE haul route approval.\n\n"
            "Fire Severity overlap: Many hillside properties are also in Very High Fire Severity Zones, requiring ember-resistant construction materials (see VHFSZ document).\n\n"
            "Tip: Order the geotechnical report as soon as the project scope is decided – it is often the longest-lead item and can delay permit issuance if not ready.\n"
        ),
    ),
    # 9 - Very High Fire Severity Zone
    KnowledgeDocument(
        id="vhfsz_requirements",
        title="Very High Fire Severity Zone (VHFSZ) – Construction Requirements",
        category="requirements",
        source="CBC Chapter 7A; LAMC Fire Code; CA Public Resources Code §4291",
        tags=["VHFSZ", "fire severity", "ember vent", "fire rating", "exterior materials", "WUI", "ignition resistant"],
        content=(
            "Very High Fire Severity Zone (VHFSZ) Construction Requirements:\n"
            "All new construction (including fire rebuilds) in VHFSZ must comply with Chapter 7A of the California Building Code:\n\n"
            "Key requirements:\n"
            "1. Roofing: Class A roof assembly required. No wood shingles.\n"
            "2. Vents: All attic vents, foundation vents, and crawl space vents must be ember-resistant (1/16-inch mesh or equivalent listed products).\n"
            "3. Exterior walls: Must achieve a 1-hour fire-resistance rating OR use ignition-resistant construction materials (e.g., stucco, fiber cement, masonry).\n"
            "4. Exterior windows: Dual-pane or multi-pane glazing required within 6 feet of grade.\n"
            "5. Decks/porches: Combustible decking materials prohibited; use Class A or non-combustible materials.\n"
            "6. Eaves: Enclosed eaves or unenclosed eaves with non-combustible materials only.\n"
            "7. Gutters: Must have metal gutters or be enclosed to prevent ember accumulation.\n\n"
            "Brush clearance:\n"
            "- LA City and County require 100-foot defensible space around structure (or to property line if lot is smaller).\n"
            "- Zone 1 (0–30 ft): Remove all dead plants, grass, and weeds.\n"
            "- Zone 2 (30–100 ft): Cut and trim plants to reduce fire fuel.\n"
        ),
    ),
    # 10 - Historic / HPOZ
    KnowledgeDocument(
        id="historic_hpoz",
        title="Historic and HPOZ Properties – Overlay Requirements",
        category="overlays",
        source="LAMC Section 12.20.3; LA Office of Historic Resources",
        tags=["historic", "HPOZ", "Mills Act", "DCP", "historic preservation", "contributing structure"],
        content=(
            "Historic Preservation Overlay Zone (HPOZ) and Historic Properties:\n\n"
            "HPOZ Review:\n"
            "- Projects in a designated HPOZ require a Certificate of Appropriateness from the Department of City Planning (DCP), Historic Preservation Unit.\n"
            "- For fire rebuilds, reconstruction of a contributing structure must generally replicate original character-defining features (materials, massing, fenestration).\n"
            "- A Historic Resources Report may be required to document the pre-fire condition.\n"
            "- Timeline: DCP HPOZ review adds 4–8 weeks to the process.\n\n"
            "Mills Act Properties:\n"
            "- If the property had an active Mills Act contract (property tax reduction in exchange for preservation), the owner must notify the Office of Historic Resources.\n"
            "- Rebuilding must comply with the Secretary of the Interior's Standards for Rehabilitation.\n"
            "- Failure to comply can result in termination of the Mills Act contract and back-taxes.\n\n"
            "Non-contributing structures in HPOZ:\n"
            "- Non-contributing structures have more flexibility but still require DCP review.\n"
            "- New construction must be compatible in scale, form, and material with the historic district character.\n\n"
            "Contact: LA Office of Historic Resources (213) 847-3679.\n"
        ),
    ),
    # 11 - LADBS plan check
    KnowledgeDocument(
        id="ladbs_plan_check",
        title="LADBS Plan Check – What Reviewers Look For and How to Expedite",
        category="process",
        source="LADBS Plan Check Procedures; CBC Title 24",
        tags=["LADBS", "plan check", "expedite", "reviewer", "corrections", "resubmittal"],
        content=(
            "LADBS Plan Check Process:\n\n"
            "What plan check reviewers examine:\n"
            "1. Zoning compliance: Setbacks, height limits, floor-area ratio (FAR), lot coverage.\n"
            "2. Structural engineering: Foundation type, shear walls, beam sizing, load path.\n"
            "3. Energy compliance: Title 24 Part 6 energy calculations (insulation, windows, HVAC).\n"
            "4. Life safety: Egress widths, smoke detectors, CO detectors, stair dimensions.\n"
            "5. Green Building (CALGreen): Mandatory measures for new construction.\n"
            "6. ADA/Accessibility: Required for ADUs and certain additions.\n\n"
            "Common reasons for plan check corrections (delays):\n"
            "- Missing or incomplete structural calculations.\n"
            "- Energy compliance forms not completed.\n"
            "- Site plan does not match legal description.\n"
            "- Inconsistencies between plan sheets (floor plan vs. elevations).\n"
            "- Missing fire sprinkler plans (required for new R-occupancy construction).\n\n"
            "How to expedite:\n"
            "- Use LADBS Standard Plans (pre-approved designs) if eligible.\n"
            "- Request an Over-the-Counter (OTC) plan check appointment for simpler projects.\n"
            "- Use self-certification by a registered architect/engineer.\n"
            "- Submit a complete, coordinated plan set on first attempt to avoid correction cycles.\n"
        ),
    ),
    # 12 - Clearance departments overview
    KnowledgeDocument(
        id="clearance_departments",
        title="Clearance Departments Overview – All Required Sign-Offs",
        category="departments",
        source="LADBS Fire Rebuild Clearance Checklist (2025)",
        tags=["clearances", "BOE", "DCP", "LAFD", "LADWP", "LASAN", "LAHD", "LA County", "departments"],
        content=(
            "Required Clearance Departments for LA Fire Rebuilds:\n\n"
            "1. Bureau of Engineering (BOE): Sewer lateral inspection, street improvements, grading/haul route.\n"
            "2. Department of City Planning (DCP): Zoning clearance, HPOZ review, Coastal Zone review (where delegated).\n"
            "3. LA Fire Department (LAFD): Fire sprinkler plans, fire flow verification, brush clearance compliance.\n"
            "4. LA Department of Water & Power (LADWP): Utility disconnection status, new service reconnection, meter reset.\n"
            "5. LA Sanitation (LASAN): Sewer connection clearance, construction waste recycling plan.\n"
            "6. LA Housing Department (LAHD): Required for multi-family (2+ units) projects; tenant relocation if applicable.\n"
            "7. LA County Assessor: Updated parcel records after demolition/rebuild.\n"
            "8. LA County Public Works (for Altadena/unincorporated areas): Entirely separate from City of LA processes.\n\n"
            "Typical clearance timeline: 2–8 weeks per department; most can run in parallel.\n"
            "Pro tip: Request a 'Concurrent Review' meeting with LADBS where representatives from multiple departments attend together – this can compress the clearance timeline significantly.\n"
        ),
    ),
    # 13 - Standard plans program
    KnowledgeDocument(
        id="standard_plans_program",
        title="Standard Plans Program – Pre-Approved Designs for R1/RE Zones",
        category="process",
        source="LADBS Standard Plans Program; LA Fire Rebuild Standard Plan Library",
        tags=["standard plans", "pre-approved", "R1", "RE zone", "time savings", "plan library"],
        content=(
            "LADBS Standard Plans Program:\n\n"
            "What it is: A library of pre-approved architectural and structural plan sets for single-family homes (R-1 and RE zones). Because these plans are already reviewed and approved by LADBS, they dramatically reduce plan check time.\n\n"
            "Time savings: Using standard plans typically saves 2–4 weeks compared to custom plans. Combined with self-certification, permit issuance can occur within 2–3 weeks of application submittal.\n\n"
            "How to use:\n"
            "1. Browse available standard plan designs in the LADBS Standard Plan Library (available on LADBS website or at permit counters).\n"
            "2. Select a design that fits the parcel (lot size, zone, desired square footage).\n"
            "3. Have a licensed architect adapt the standard plan for site-specific conditions (soil type, topography, specific parcel dimensions).\n"
            "4. Submit the adapted plan set with the standard plan reference number.\n\n"
            "Limitations:\n"
            "- Standard plans are only available for certain R-1 and RE zone configurations.\n"
            "- Not available for hillside parcels with unusual topography.\n"
            "- Not available for HPOZ properties (historic design review required).\n"
            "- The standard plan must be adapted for each specific lot – a licensed architect must review and stamp the adapted plans.\n"
        ),
    ),
    # 14 - BOE clearances
    KnowledgeDocument(
        id="boe_clearances",
        title="Bureau of Engineering (BOE) – Sewer, Street, and Haul Route Clearances",
        category="departments",
        source="LA Bureau of Engineering; LAMC Section 64.30",
        tags=["BOE", "sewer lateral", "street improvements", "haul route", "grading", "Bureau of Engineering"],
        content=(
            "Bureau of Engineering (BOE) Clearances for Fire Rebuilds:\n\n"
            "1. Sewer Lateral Inspection and Clearance:\n"
            "   - A CCTV inspection of the existing sewer lateral is required before reconnection.\n"
            "   - If lateral is damaged or does not meet current standards, repair or replacement is required.\n"
            "   - Processing time: 2–4 weeks.\n\n"
            "2. Street Improvements:\n"
            "   - BOE may require curb, gutter, or sidewalk repairs or upgrades as a condition of the permit.\n"
            "   - 'Notice to Improve' orders are common in older neighborhoods.\n"
            "   - Can be deferred with a bond or cash deposit if construction would damage newly-installed street improvements.\n\n"
            "3. Haul Route Approval:\n"
            "   - Required for transporting demolition debris or construction materials through residential or sensitive streets.\n"
            "   - Haul routes must avoid school zones and weight-restricted streets.\n"
            "   - BOE reviews and approves the route; typically takes 1–2 weeks.\n\n"
            "4. Grading Permit (if applicable):\n"
            "   - Required for grading more than 50 cubic yards.\n"
            "   - Grading plans must be stamped by a licensed civil engineer.\n"
        ),
    ),
    # 15 - LAFD requirements
    KnowledgeDocument(
        id="lafd_requirements",
        title="LAFD Requirements – Fire Sprinklers, Fire Flow, and Brush Clearance",
        category="departments",
        source="LA Fire Code (LAFC); California Fire Code (CFC); LAMC Chapter IX",
        tags=["LAFD", "fire sprinklers", "fire flow", "brush clearance", "fire department", "NFPA 13D"],
        content=(
            "LA Fire Department (LAFD) Requirements for New Construction:\n\n"
            "1. Fire Sprinkler System:\n"
            "   - Required for ALL new one- and two-family dwellings (R-3 occupancy) per California Residential Code Section R313.\n"
            "   - System must comply with NFPA 13D or California Residential Code R313.\n"
            "   - Fire sprinkler plans must be submitted to LAFD for approval before permit issuance.\n"
            "   - LAFD plan check for sprinklers: 2–4 weeks.\n\n"
            "2. Fire Flow:\n"
            "   - LAFD verifies that the water supply (hydrant flow) is adequate for fire suppression.\n"
            "   - If flow is insufficient, applicant may need to install a fire water storage tank or upgrade service.\n\n"
            "3. Brush Clearance Inspection:\n"
            "   - Before final permit issuance (Certificate of Occupancy), LAFD will conduct a brush clearance inspection.\n"
            "   - Brush clearance zones: 100 ft from structure (or property line) for hillside/VHFSZ properties.\n\n"
            "4. Access Road:\n"
            "   - All-weather fire access road (minimum 20 ft wide, 13.5 ft vertical clearance) must be maintained.\n"
            "   - Dead-end roads longer than 150 ft require an approved turnaround.\n"
        ),
    ),
    # 16 - LADWP reconnection
    KnowledgeDocument(
        id="ladwp_reconnection",
        title="LADWP – Utility Reconnection Process and Timeline",
        category="departments",
        source="LA Department of Water & Power (LADWP) Rebuild Services",
        tags=["LADWP", "utility", "reconnection", "electric", "water", "meter", "service"],
        content=(
            "LADWP Utility Reconnection for Fire Rebuilds:\n\n"
            "Steps to restore utility service:\n"
            "1. Confirm disconnection: LADWP should have disconnected services after the fire. Verify the account status.\n"
            "2. Electrical service application: Submit a new service application to LADWP during the design phase. Specify new panel size and location.\n"
            "3. Temporary power: Request temporary construction power early – this is separate from permanent service.\n"
            "4. Water service: Confirm water meter size is adequate for the new home's fixtures and fire sprinkler demand.\n"
            "5. Final inspection: LADWP will inspect new service equipment (panel, meter base, water lines) before permanent reconnection.\n"
            "6. Service energization: After LADWP final inspection and LADBS final inspection, LADWP schedules energization.\n\n"
            "Timeline: Reconnection process typically takes 2–4 weeks from application to energization.\n"
            "Delays: Transformer upgrades or underground service work can add 4–8 additional weeks.\n\n"
            "LADWP Fire Rebuild Hotline: (800) DIAL-DWP (800-342-5397)\n"
            "LADWP expedited fire rebuild team: Contact the LADWP Fire Rebuild Customer Service Center.\n"
        ),
    ),
    # 17 - Timeline by pathway
    KnowledgeDocument(
        id="timeline_by_pathway",
        title="Permit Timeline by Pathway – Detailed Phase Breakdown",
        category="timeline",
        source="LADBS Fire Rebuild Program Overview (2025)",
        tags=["timeline", "EO1", "EO8", "standard", "phases", "duration", "comparison"],
        content=(
            "Permit Timeline Comparison by Pathway:\n\n"
            "EO1 Like-for-Like (fastest):\n"
            "  - Total: 45–120 days\n"
            "  - Plan preparation: 1–3 weeks\n"
            "  - LADBS plan check: 2–4 weeks (1–2 weeks with standard plans or self-cert)\n"
            "  - Clearances (parallel): 2–6 weeks\n"
            "  - Permit issuance: 1–3 business days\n\n"
            "EO8 Expanded:\n"
            "  - Total: 90–180 days\n"
            "  - Plan preparation: 2–5 weeks\n"
            "  - LADBS plan check: 4–8 weeks\n"
            "  - Clearances (parallel): 4–10 weeks\n"
            "  - DCP review (if triggered): +4–8 weeks\n"
            "  - Coastal CDP (if applicable): +30–60 days\n"
            "  - Permit issuance: 1–5 business days\n\n"
            "Standard Permitting (no EO):\n"
            "  - Total: 180+ days (up to 12–18 months for complex projects)\n"
            "  - Discretionary review (DCP): 8–24 weeks\n"
            "  - CEQA review: 4–12 weeks additional\n"
            "  - LADBS plan check: 6–12 weeks\n"
            "  - Clearances: 4–12 weeks\n\n"
            "Note: All timelines assume a complete, accurate application on first submittal. Each correction cycle adds 2–4 weeks.\n"
        ),
    ),
    # 18 - Common delays
    KnowledgeDocument(
        id="common_delays",
        title="Common Permit Delays and How to Avoid Them",
        category="process",
        source="LADBS Permit Expediting Best Practices; LA Fire Rebuild Coalition Guidance",
        tags=["delays", "avoid", "tips", "incomplete plans", "soils report", "corrections", "expedite"],
        content=(
            "Top Causes of Permit Delays and How to Avoid Them:\n\n"
            "1. Incomplete or inconsistent plans:\n"
            "   - Problem: Plan sheets contradict each other (floor plan vs. elevation dimensions differ).\n"
            "   - Fix: Have a licensed architect perform a quality-control review before submittal.\n\n"
            "2. Missing soils/geotechnical report (hillside only):\n"
            "   - Problem: Soils report not ordered early enough – can take 3–6 weeks to complete.\n"
            "   - Fix: Order the soils report at the same time as hiring the architect.\n\n"
            "3. Unpaid prior fees or open violations:\n"
            "   - Problem: LADBS flags the property for unpaid fees or unresolved code violations from before the fire.\n"
            "   - Fix: Run a LADBS property record search and resolve outstanding issues before applying.\n\n"
            "4. Title/ownership issues:\n"
            "   - Problem: Probate, trusts, or liens that complicate ownership verification.\n"
            "   - Fix: Consult a real estate attorney early; have clear title documentation ready.\n\n"
            "5. Delayed clearances from other departments:\n"
            "   - Problem: Waiting for one department while others are ready.\n"
            "   - Fix: Submit to all clearance departments simultaneously; follow up weekly.\n\n"
            "6. Fire sprinkler plan not submitted:\n"
            "   - Problem: Applicant forgets that LAFD sprinkler plan check is separate from LADBS plan check.\n"
            "   - Fix: Submit sprinkler plans to LAFD at the same time as LADBS plan check submittal.\n\n"
            "7. LADWP service upgrade required:\n"
            "   - Problem: Larger home or EV charging requires panel/transformer upgrade.\n"
            "   - Fix: Consult LADWP early in design to confirm service capacity.\n"
        ),
    ),
    # 19 - Required documents checklist
    KnowledgeDocument(
        id="required_documents",
        title="Complete Document Checklist for Permit Application",
        category="documents",
        source="LADBS Fire Rebuild Application Checklist (2025)",
        tags=["documents", "checklist", "application", "required", "submittal", "forms"],
        content=(
            "Complete Permit Application Document Checklist (Fire Rebuild):\n\n"
            "Ownership and Property:\n"
            "- [ ] Completed LADBS Permit Application form (online or in-person)\n"
            "- [ ] Proof of ownership (Grant Deed, Title Report, or Assessor records)\n"
            "- [ ] Government-issued photo ID\n"
            "- [ ] HOA approval letter (if applicable)\n\n"
            "Damage Verification:\n"
            "- [ ] Fire department incident report (LAFD or CAL FIRE)\n"
            "- [ ] LADBS damage assessment report (if issued)\n"
            "- [ ] Insurance claim summary (optional but helpful)\n\n"
            "Design Plans (to be prepared by licensed architect/engineer):\n"
            "- [ ] Site plan: property lines, proposed structure footprint, setbacks, north arrow, scale\n"
            "- [ ] Floor plan(s): room labels, dimensions, door/window locations\n"
            "- [ ] Elevations (all four sides)\n"
            "- [ ] Building sections\n"
            "- [ ] Foundation plan and details\n"
            "- [ ] Structural calculations (engineer-stamped)\n"
            "- [ ] Energy compliance forms (CF-1R or equivalent Title 24 Part 6 documentation)\n"
            "- [ ] CalGreen checklist\n\n"
            "Special Reports (as applicable):\n"
            "- [ ] Soils/geotechnical report (hillside parcels)\n"
            "- [ ] Title 24 Part 2 structural/seismic calculations\n"
            "- [ ] Historic resources report (HPOZ properties)\n"
            "- [ ] Coastal zone determination letter (coastal properties)\n\n"
            "Clearance-Specific Submittals:\n"
            "- [ ] Fire sprinkler plans (to LAFD)\n"
            "- [ ] Sewer lateral CCTV video (to BOE)\n"
            "- [ ] Grading plan (to BOE, if >50 CY of grading)\n"
            "- [ ] LADWP new service application\n"
        ),
    ),
    # 20 - Fee schedule overview
    KnowledgeDocument(
        id="fee_schedule",
        title="Fee Schedule Overview – Plan Check, Permit, and Inspection Fees",
        category="costs",
        source="LADBS Fee Schedule (FY 2024–25); LA City Clerk Fee Ordinance",
        tags=["fees", "cost", "plan check fee", "permit fee", "inspection fee", "LADBS fees"],
        content=(
            "LA Permit Fee Overview for Fire Rebuilds:\n\n"
            "Note: Fees are based on construction valuation and are subject to change. Many fire-rebuild fees were reduced or waived under emergency orders – confirm current fee schedule with LADBS.\n\n"
            "Plan Check Fee:\n"
            "- Typically 70–85% of the permit fee.\n"
            "- For a 2,000 sq ft home at ~$250/sq ft valuation ($500,000 value), plan check fee is approximately $2,000–$4,000.\n"
            "- Expedited plan check: additional 50–100% surcharge.\n\n"
            "Building Permit Fee:\n"
            "- Based on construction valuation table (LADBS publishes annual valuation multipliers).\n"
            "- Rough estimate: $3,000–$8,000 for a typical single-family home rebuild.\n\n"
            "Inspection Fees:\n"
            "- Included in permit fee for standard inspections.\n"
            "- After-hours or weekend inspections: additional $300–$600 per inspection.\n\n"
            "Other fees:\n"
            "- BOE sewer connection fee: $500–$2,000 depending on lot size.\n"
            "- LAFD fire sprinkler plan check: $500–$1,500.\n"
            "- School development fee (if applicable): ~$4.08/sq ft for residential.\n"
            "- Grading permit: $1,000–$5,000 depending on volume.\n\n"
            "Fee waivers: Under the 2025 emergency orders, LADBS waived or reduced certain plan check and permit fees for fire-rebuild projects. Contact LADBS to confirm current waivers.\n"
        ),
    ),
    # 21 - Altadena specific rules
    KnowledgeDocument(
        id="altadena_rules",
        title="Altadena – Unincorporated LA County Rules and Process",
        category="process",
        source="LA County Department of Regional Planning; LA County Public Works",
        tags=["Altadena", "unincorporated", "LA County", "county permits", "different process"],
        content=(
            "Altadena and Unincorporated LA County – Different from City of LA:\n\n"
            "IMPORTANT: Altadena is an unincorporated community in LA County, NOT part of the City of Los Angeles. This means:\n"
            "- Permits are issued by LA County Building & Safety (not LADBS).\n"
            "- Zoning is governed by LA County Department of Regional Planning (not City Planning).\n"
            "- Water service may be through Pasadena Water & Power or other local agencies (not LADWP).\n\n"
            "LA County fire-rebuild pathways (parallel to City EO programs):\n"
            "- LA County also issued emergency orders for fire rebuild streamlining.\n"
            "- Contact LA County Building & Safety at (626) 458-3100 for current pathway options.\n"
            "- LA County Building & Safety permit portal: builderpermits.lacounty.gov\n\n"
            "Key differences from City of LA process:\n"
            "- Different fee schedule.\n"
            "- Different plan check reviewers and processes.\n"
            "- LA County Flood Control District may have additional requirements for grading/drainage.\n"
            "- Altadena Town & Community Council (not an official body) provides community input but no formal approval authority.\n\n"
            "If your address is in Altadena, do NOT apply through the City of LA LADBS portal – use the LA County portal instead.\n"
        ),
    ),
    # 22 - Emergency Executive Orders overview
    KnowledgeDocument(
        id="executive_orders_overview",
        title="Emergency Executive Orders – EO1 Through EO9 Overview",
        category="eligibility",
        source="Mayor's Office; LA City Clerk Executive Order Registry (2025)",
        tags=["executive order", "EO1", "EO2", "EO3", "EO4", "EO5", "EO6", "EO7", "EO8", "EO9", "emergency", "overview"],
        content=(
            "LA Mayor's Emergency Executive Orders for Fire Rebuild (2025):\n\n"
            "EO1 – Like-for-Like Rebuild (Effective: January 2025)\n"
            "  Allows rebuilding to match original structure with up to 10% size increase.\n"
            "  Fastest pathway; LADBS expedited review.\n\n"
            "EO2 – Debris Removal Coordination (Effective: January 2025)\n"
            "  Streamlined Army Corps of Engineers and CalOES debris removal process.\n"
            "  Removal is prerequisite for permit application.\n\n"
            "EO3 – Temporary Housing Relief (Effective: January 2025)\n"
            "  Expedited ADU and temporary shelter permitting for displaced residents.\n\n"
            "EO4 – Contractor Fraud Protections (Effective: February 2025)\n"
            "  Enhanced licensing verification requirements for contractors working on fire rebuilds.\n\n"
            "EO5 – Environmental Review Streamlining (Effective: February 2025)\n"
            "  Categorical exemptions from CEQA for EO1-eligible projects.\n\n"
            "EO6 – Fee Waivers (Effective: February 2025)\n"
            "  Waives or reduces LADBS plan check and permit fees for qualifying fire-rebuild projects.\n\n"
            "EO7 – Rental Housing Protections (Effective: February 2025)\n"
            "  Price-gouging restrictions and relocation assistance for fire-displaced renters.\n\n"
            "EO8 – Expanded Rebuild Pathway (Effective: March 2025)\n"
            "  Allows rebuilding up to 150% of original size with new footprint permitted.\n\n"
            "EO9 – Construction Workforce Provisions (Effective: March 2025)\n"
            "  Local hire requirements and prevailing wage guidance for fire-rebuild projects.\n\n"
            "All EOs are subject to amendment; verify current status at lamayor.org or lacity.gov/rebuild.\n"
        ),
    ),
]


# ---------------------------------------------------------------------------
# KnowledgeBase class
# ---------------------------------------------------------------------------


class KnowledgeBase:
    """In-memory knowledge base with TF-IDF or keyword-based retrieval."""

    def __init__(self) -> None:
        self._documents = PERMIT_KNOWLEDGE
        self._use_sklearn = False
        self._vectorizer = None
        self._doc_matrix = None

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401

            self._use_sklearn = True
            self._build_tfidf_index()
        except ImportError:
            self._build_inverted_index()

    # ------------------------------------------------------------------
    # Index builders
    # ------------------------------------------------------------------

    def _doc_text(self, doc: KnowledgeDocument) -> str:
        """Concatenate all searchable fields of a document into one string."""
        tag_text = " ".join(doc.tags)
        return f"{doc.title} {tag_text} {doc.content}"

    def _build_tfidf_index(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )
        corpus = [self._doc_text(d) for d in self._documents]
        self._doc_matrix = self._vectorizer.fit_transform(corpus)

    def _build_inverted_index(self) -> None:
        """Build a simple word -> document-index inverted index as a fallback."""
        self._inverted_index: dict[str, list[int]] = {}
        for idx, doc in enumerate(self._documents):
            words = set(re.findall(r"[a-z0-9]+", self._doc_text(doc).lower()))
            for word in words:
                self._inverted_index.setdefault(word, []).append(idx)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeDocument]:
        """Return the *top_k* most relevant documents for *query*."""
        if self._use_sklearn:
            return self._tfidf_search(query, top_k)
        return self._keyword_search(query, top_k)

    def get_by_category(self, category: str) -> list[KnowledgeDocument]:
        """Return all documents whose category matches *category* (case-insensitive)."""
        category_lower = category.lower()
        return [d for d in self._documents if d.category.lower() == category_lower]

    # ------------------------------------------------------------------
    # Private search implementations
    # ------------------------------------------------------------------

    def _tfidf_search(self, query: str, top_k: int) -> list[KnowledgeDocument]:
        """Rank documents using TF-IDF cosine similarity via sklearn."""
        from sklearn.metrics.pairwise import cosine_similarity

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._doc_matrix).flatten()
        top_indices = scores.argsort()[::-1][:top_k]
        return [self._documents[i] for i in top_indices if scores[i] > 0]

    def _keyword_search(self, query: str, top_k: int) -> list[KnowledgeDocument]:
        """Rank documents by counting overlapping keywords with the query."""
        query_words = Counter(re.findall(r"[a-z0-9]+", query.lower()))
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "in", "of", "to", "for", "and", "or",
            "my", "i", "what", "how", "do", "does", "can", "will", "be",
            "are", "was", "were", "it", "this", "that", "with", "on", "at",
        }
        query_words = Counter(
            {w: c for w, c in query_words.items() if w not in stop_words}
        )

        if not query_words:
            return self._documents[:top_k]

        scores: list[tuple[float, int]] = []
        for idx, doc in enumerate(self._documents):
            doc_text = self._doc_text(doc).lower()
            doc_words = Counter(re.findall(r"[a-z0-9]+", doc_text))

            # Compute a simple dot product normalized by document length
            dot = sum(query_words[w] * doc_words[w] for w in query_words)
            doc_norm = math.sqrt(sum(v ** 2 for v in doc_words.values())) or 1.0
            query_norm = math.sqrt(sum(v ** 2 for v in query_words.values())) or 1.0
            cosine = dot / (doc_norm * query_norm)
            scores.append((cosine, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            self._documents[idx]
            for score, idx in scores[:top_k]
            if score > 0
        ]
