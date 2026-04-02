---
sidebar_position: 2
title: Permit Pathways
---

# Permit Pathways

After the LA wildfires, the city issued Executive Orders creating expedited permit pathways for fire rebuilds.

## Pathway Comparison

| Feature | EO1 Like-for-Like | EO8 Expanded | Standard |
|---------|-------------------|--------------|----------|
| Max sqft increase | 10% | 50% | No limit |
| Estimated timeline | 45-120 days | 90-180 days | 180+ days |
| Clearances required | Fewer | Moderate | Full suite |
| AI pathway code | `eo1_like_for_like` | `eo8_expanded` | `standard` |

## EO1 -- Like-for-Like Rebuild

**Executive Order 1** provides the fastest pathway for rebuilding a destroyed home to substantially the same size and configuration.

**Eligibility:**
- Property must be in a designated fire area
- Proposed sqft within 10% of original
- Rebuild on same footprint
- Same number of units

**Benefits:**
- Expedited plan check (often same-day)
- Reduced clearance requirements
- Waived or reduced fees
- Self-certification option for some components

**Limitations:**
- Cannot significantly change the home's footprint
- Cannot add stories beyond original
- Overlay zones may add requirements (coastal, hillside)

## EO8 -- Expanded Rebuild

**Executive Order 8** allows larger rebuilds while still benefiting from expedited processing.

**Eligibility:**
- Property must be in a designated fire area
- Proposed sqft within 50% of original
- Must meet zoning requirements for increased size

**Benefits:**
- Faster than standard process
- Flexibility to make the home larger
- Some fee reductions

**Conditional Requirements:**
- 10-30% increase: additional zoning review
- 30-50% increase: may require additional plan check
- Overlay zones add requirements

## Standard Pathway

The standard permit pathway applies when a project exceeds EO8 limits or is not in a designated fire area.

**Requirements:**
- Full plan check and review
- All departmental clearances
- Complete fee schedule
- Standard processing timelines

## Pathway Determination

PathfinderAI evaluates pathways in priority order:
1. Try **EO1** (fastest) -- return if eligible
2. Try **EO8** (intermediate) -- return if eligible
3. Fall back to **Standard** (always eligible)

The rules engine has veto power over AI recommendations. If the rules engine determines a project is not EO1-eligible, Claude AI cannot override that determination.
