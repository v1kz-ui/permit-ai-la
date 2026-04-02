---
sidebar_position: 5
title: Inspections
---

# Inspections API

Schedule and track building inspections.

## Schedule Inspection

```
POST /api/v1/inspections
```

```json
{
  "project_id": "uuid",
  "inspection_type": "Foundation",
  "scheduled_date": "2026-05-15T09:00:00Z",
  "inspector_name": "J. Rodriguez",
  "notes": "Access from rear alley"
}
```

## List Inspections

```
GET /api/v1/inspections?project_id={uuid}
```

Returns all inspections for the project.

## Update Inspection

```
PATCH /api/v1/inspections/{inspection_id}
```

```json
{
  "status": "passed",
  "completed_date": "2026-05-15T14:30:00Z",
  "notes": "All items satisfactory"
}
```

For failed inspections, include failure reasons:
```json
{
  "status": "failed",
  "failure_reasons": ["Framing not per approved plans", "Missing fire blocking"]
}
```

## Inspection Types

Standard construction sequence:
- Foundation, Framing
- Rough electrical, Rough plumbing, Rough mechanical
- Insulation, Drywall
- Final electrical, Final plumbing, Final mechanical, Final building
- Grading (pre and final)
- Fire sprinkler, Fire final

## Status Values

```
scheduled | passed | failed | completed_pass | completed_fail | cancelled | no_show
```
