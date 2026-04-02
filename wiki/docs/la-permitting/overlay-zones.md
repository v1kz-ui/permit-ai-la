---
sidebar_position: 4
title: Overlay Zones
---

# Overlay Zones

Overlay zones are special designations that add requirements on top of base zoning. They significantly impact permit timelines and required clearances.

## Zone Types

### Coastal Zone
**Flag:** `is_coastal_zone`

Properties within the California Coastal Zone require additional review under the Coastal Act.

**Impact:**
- Additional DCP clearance: Coastal Development Permit
- Timeline multiplier: 1.3x
- May require California Coastal Commission review

### Hillside
**Flag:** `is_hillside`

Properties on sloped terrain with additional structural and environmental requirements.

**Impact:**
- LADBS: Hillside Grading Review
- BOE: Hillside Drainage Review, Haul Route Approval
- Timeline multiplier: 1.25x

### Very High Fire Hazard Severity Zone (VHFSZ)
**Flag:** `is_very_high_fire_severity`

Areas designated as high risk for wildfire. Most fire rebuild projects are in these zones.

**Impact:**
- LAFD: Fire Hazard Zone Review, Brush Clearance Verification, Fire Flow check
- Enhanced fire safety requirements (sprinklers, fire-resistant materials)
- Timeline multiplier: 1.15x

### Historic / HPOZ
**Flags:** `is_historic`, `has_hpoz`

Properties with historic designation or within a Historic Preservation Overlay Zone.

**Impact:**
- DCP: Historic Preservation Review, HPOZ Board Review
- Cultural Affairs: Cultural Resource Review
- Timeline multiplier: 1.2x
- Restrictions on exterior modifications

### Flood Zone
**Flag:** `is_flood_zone`

Properties in FEMA-designated flood areas.

**Impact:**
- BOE: Flood Zone Review
- Timeline multiplier: 1.1x
- Elevated foundation requirements

### Geological Hazard
**Flag:** `is_geological_hazard`

Properties in areas with known geological instability.

**Impact:**
- LADBS: Geotechnical Review
- LA County: Geotechnical/Soils Report Review
- Timeline multiplier: 1.2x
- Soils report required

## Compound Effects

Overlay multipliers compound when a parcel has multiple designations:

**Example:** A coastal + hillside + fire severity parcel:
- 1.3 x 1.25 x 1.15 = **1.87x** baseline processing time
- Requires clearances from: DCP (coastal), LADBS (hillside grading), BOE (drainage), LAFD (fire safety)

This is why PathfinderAI's overlay detection is critical -- it automatically identifies all applicable overlays from ZIMAS parcel data and calculates the compound impact.
