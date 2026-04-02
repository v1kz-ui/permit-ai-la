---
sidebar_position: 5
title: What-If Analysis
---

# What-If Scenario Analysis

Compare permit timelines and requirements across different rebuild scopes.

## How It Works

The What-If page (`/projects/[id]/what-if`) lets staff and homeowners explore:
- **Current plan** -- The project as currently scoped
- **EO1 Maximum** -- What if the rebuild stays within 10% sqft increase?
- **EO8 Maximum** -- What if the rebuild stays within 50% sqft increase?

Each scenario card shows:
- Pathway badge (EO1/EO8/Standard)
- Estimated days to completion (large bold number)
- List of constraints and requirements
- Relative bar chart for visual comparison

## API Endpoint

```
POST /api/v1/pathfinder/what-if
```

Input:
```json
{
  "address": "123 Fire Rd, Los Angeles, CA",
  "original_sqft": 2000,
  "proposed_sqft": 2500,
  "stories": 2
}
```

The endpoint evaluates all three scenarios simultaneously and returns an AI recommendation for the optimal pathway.

## Use Cases

- **Homeowner planning** -- Understand trade-offs between rebuild size and permit timeline
- **Contractor advising** -- Show clients quantified impact of scope changes
- **Staff consultation** -- Help applicants understand why pathway X is faster than Y

## Reference Boxes

The UI includes quick-reference boxes explaining:
- **EO1:** Max 10% increase from original sqft
- **EO8:** Max 50% increase from original sqft
