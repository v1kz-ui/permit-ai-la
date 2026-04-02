---
sidebar_position: 4
title: PathfinderAI
---

# PathfinderAI API

AI-powered permit pathway analysis endpoints.

## Full Analysis

```
POST /api/v1/pathfinder/analyze/{project_id}
```

Runs the complete analysis pipeline: rules engine, Claude AI (if needed), standard plan matching, timeline prediction, and conflict detection.

**Response includes:**
- `pathway` -- Recommended pathway
- `eligibility` -- EO1/EO8/Standard eligibility results
- `clearances` -- Required clearances list
- `ai_analysis` -- Claude reasoning (if triggered)
- `standard_plans` -- Compatible pre-approved plans
- `timeline` -- Predicted days with department breakdown
- `conflicts` -- Clearance ordering conflicts

## Quick Analysis

```
POST /api/v1/pathfinder/quick-analysis
```

Fast pathway estimate from address only (no project needed).

```json
{
  "address": "123 Fire Rd, Los Angeles, CA",
  "original_sqft": 2000,
  "proposed_sqft": 2200,
  "stories": 2
}
```

**Response:**
```json
{
  "pathway": "eo1_like_for_like",
  "eligible": true,
  "reasons": ["Within 10% sqft increase"],
  "required_clearances": ["Zoning Clearance", "..."],
  "estimated_days": 75,
  "parcel_found": true,
  "overlays": {"is_coastal_zone": false, "is_hillside": true}
}
```

## Conflict Detection

```
GET /api/v1/pathfinder/conflicts/{project_id}
```

Identifies clearances that have sequential dependencies.

## Timeline Prediction

```
GET /api/v1/pathfinder/timeline/{project_id}
```

Returns predicted timeline with critical path analysis.

## What-If Scenarios

```
POST /api/v1/pathfinder/what-if
```

Compares current plan, EO1 max, and EO8 max scenarios side-by-side.
