---
sidebar_position: 1
title: PathfinderAI
---

# PathfinderAI

PathfinderAI is the core decision engine that determines the optimal permit pathway for fire rebuild projects.

## How It Works

PathfinderAI uses a two-tier approach: a deterministic rules engine evaluated first, with Claude AI called only for edge cases.

```
Address + Scope → Parcel Lookup → Rules Engine → [Claude AI if needed] → Pathway Result
                                       │                    │
                                       ▼                    ▼
                              Standard Plans ←── Timeline Prediction
                                 Matching            (XGBoost)
```

## Rules Engine (Deterministic)

**File:** `backend/app/ai/pathfinder/rules_engine.py`

The rules engine evaluates versioned JSON rule files in priority order:

1. **EO1 Like-for-Like** (fastest, ~45-120 days)
   - Max 10% square footage increase
   - Must rebuild on same footprint
   - Fewer clearances required

2. **EO8 Expanded** (intermediate, ~90-180 days)
   - Max 50% square footage increase
   - Additional clearances for larger increases
   - Conditional requirements based on overlay zones

3. **Standard** (fallback, ~180+ days)
   - Always eligible
   - Full clearance suite required
   - No sqft limitations

The rules engine has **absolute veto power** over AI recommendations. If the rules engine says a project is not EO1-eligible, Claude cannot override that.

### Rule Files

JSON rule definitions in `backend/app/ai/pathfinder/rules/`:
- `eo1_like_for_like.json` -- EO1 eligibility constraints
- `eo8_expanded.json` -- EO8 eligibility constraints
- `coastal_zone.json` -- Coastal overlay requirements
- `hillside.json` -- Hillside overlay requirements

## Claude AI Reasoner (Edge Cases)

**File:** `backend/app/ai/pathfinder/claude_reasoner.py`

Called only when the rules engine cannot confidently determine a pathway:
- Unusual zoning overlay combinations
- Conflicting requirements across departments
- Ambiguous project scope descriptions

Claude returns structured JSON:
```json
{
  "recommended_pathway": "eo8_expanded",
  "confidence": 0.82,
  "reasoning": "explanation of edge case analysis",
  "additional_clearances": ["Coastal Development Review"],
  "risk_factors": ["Adjacent to HPOZ boundary"],
  "estimated_days_adjustment": 15
}
```

### Veto System

Claude cannot recommend a faster pathway than the rules engine. Pathway speed ranking:
- `self_certification` (0) < `eo1` (1) < `eo8` (2) < `standard` (3)

If Claude suggests EO1 but rules say EO8, the rules engine wins and `rules_engine_vetoed = true`.

## Standard Plan Matching

**File:** `backend/app/ai/pathfinder/standard_plan_matcher.py`

Finds pre-approved construction plans compatible with:
- Lot dimensions (width, depth, area)
- Zoning classification
- Number of stories

Using a standard plan can significantly reduce design review time.

## Full Analysis Pipeline

The `POST /api/v1/pathfinder/analyze/{project_id}` endpoint runs:
1. Rules engine evaluation (all pathways)
2. Claude AI reasoning (if needed)
3. Standard plan matching
4. Timeline prediction
5. Conflict detection

Returns a comprehensive `PathfinderAnalysisResponse`.
