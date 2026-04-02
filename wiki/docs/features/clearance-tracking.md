---
sidebar_position: 2
title: Clearance Tracking
---

# Multi-Department Clearance Tracking

Every fire rebuild permit requires clearances from multiple LA city departments. PermitAI tracks these in real-time.

## Departments

PermitAI tracks clearances across 10 LA departments plus LA County:

| Department | Code | Role |
|-----------|------|------|
| Dept. of Building & Safety | `ladbs` | Building permits, structural review, grading |
| Dept. of City Planning | `dcp` | Zoning, HPOZ, coastal development, historic preservation |
| Bureau of Engineering | `boe` | Sewers, street improvements, haul routes |
| Fire Department | `lafd` | Fire/life safety, brush clearance, sprinklers |
| Dept. of Water & Power | `ladwp` | Water/electrical service connections |
| LA Sanitation & Environment | `lasan` | Sewer connections, LID compliance |
| Housing Department | `lahd` | Multi-family housing, rent stabilization |
| Dept. of Transportation | `dot` | Driveway access, traffic studies |
| Cultural Affairs | `cultural_affairs` | Cultural/archaeological resource review |
| Urban Forestry | `urban_forestry` | Protected tree removal, replacement plans |
| LA County | `la_county` | Geotechnical review, flood zone compliance |

## Clearance Statuses

| Status | Description |
|--------|-------------|
| `not_started` | Clearance has not been submitted |
| `in_review` | Under review by the department |
| `approved` | Clearance granted |
| `conditional` | Approved with conditions |
| `denied` | Clearance denied |
| `not_applicable` | Not required for this project |

## Auto-Generation

When a project is created, clearances are automatically generated based on parcel overlay flags.

**Baseline clearances** (every project):
- LADBS: Zoning Clearance
- BOE: Sewer Capacity Clearance
- LADWP: Power/Water Clearance
- LASAN: Sanitation Clearance

**Conditional clearances** (based on parcel flags):

| Parcel Flag | Department | Clearance |
|------------|-----------|-----------|
| `is_coastal_zone` | DCP | Coastal Development Permit |
| `is_hillside` | LADBS | Hillside Grading Review |
| `is_hillside` | BOE | Hillside Drainage Review |
| `is_very_high_fire_severity` | LAFD | Fire Hazard Zone Review |
| `is_historic` | DCP | Historic Preservation Review |
| `is_historic` | Cultural Affairs | Cultural Resource Review |
| `is_flood_zone` | BOE | Flood Zone Review |
| `is_geological_hazard` | LADBS | Geotechnical Review |
| `has_hpoz` | DCP | HPOZ Board Review |

## Kanban Board

The staff dashboard includes a drag-and-drop Kanban board at `/clearances`:

- **5 columns:** Not Started, In Review, Approved, Conditional, Denied
- **Drag-and-drop** to change status (powered by dnd-kit)
- **5-second undo window** after each move
- **Department filter** to focus on specific departments
- **Bottleneck indicators** (red border + animated dot) for flagged clearances

## Real-Time Updates

Clearance status changes emit events via Redis pub/sub, which are broadcast to connected WebSocket clients for real-time dashboard updates.

## Conflict Detection

Some clearances have sequential dependencies. The conflict detection service identifies clearances that cannot proceed in parallel (e.g., hillside geotechnical review must complete before grading permit approval).
