---
sidebar_position: 8
title: Inspector Routing
---

# Inspector Routing

Geographic clustering for optimal inspection scheduling and route planning.

## How It Works

The routing page (`/inspections/routing`) groups inspections by geographic area and assigns inspectors to minimize drive time.

## Dashboard Features

- **3 stat cards:** Inspections today, Inspectors active, Avg drive time
- **Cluster cards** grouped by geographic area:
  - Area name and assigned inspector
  - Drive time estimate
  - List of inspections with time, address, and type
  - Color-coded by inspector (indigo, emerald, amber, violet)
- **Map placeholder** for Mapbox GL visualization (requires token)
- "Geographic clustering active" indicator

## Inspection Management

The inspections page (`/inspections`) provides:

- **4 KPI cards:** Total scheduled, Pass rate, Avg days between, Most common failure
- **Filters:** Status, type, search by address
- **Table:** Address, type, status, dates, inspector, notes/failure reasons
- **Schedule modal:** Create new inspections with project, type, date, inspector, notes

## Inspection Types

Inspections follow the construction sequence:
1. Foundation
2. Framing
3. Rough electrical / plumbing / mechanical
4. Insulation
5. Drywall
6. Final electrical / plumbing / mechanical / building
7. Grading (pre and final)
8. Fire sprinkler and fire final
