---
sidebar_position: 9
title: Analytics
---

# Analytics Dashboard

Comprehensive performance metrics, equity analysis, and trend visualization for staff and administrators.

## Dashboard Page

The analytics page (`/analytics`) includes:

### KPI Cards
- **Active Projects** -- Total projects in pipeline
- **Completion Rate** -- Percentage of projects with all clearances approved
- **Avg Days to Issue** -- Mean processing time
- **Active Bottlenecks** -- Number of flagged clearances

### Department Performance Chart
Stacked bar chart showing clearances by department, color-coded:
- Green: no bottlenecks
- Amber: some bottlenecks
- Red: high bottleneck count

### Trends Chart
Switchable time-series chart:
- **Metrics:** Permits issued, Clearances completed, Bottlenecks
- **Periods:** 7 days, 30 days, 90 days

### Equity Metrics
Table showing per-area breakdown:
- Area name
- Project count
- Average predicted days
- Average actual days

Identifies disparities in processing time across neighborhoods.

### Additional Sections
- **Language Distribution** -- Counts by supported language
- **Pathway Distribution** -- Counts and avg days per pathway
- **Active Bottlenecks** -- Detailed list of problematic clearances

### CSV Export
Download analytics data for external analysis via the export button.

## API Endpoints

```
GET /api/v1/analytics/pipeline                    # Completion rates, avg days, bottleneck frequency
GET /api/v1/analytics/geographic                  # Heatmap data
GET /api/v1/analytics/department/{dept}            # Department performance metrics
GET /api/v1/analytics/trends?metric=&period=       # Time series data
GET /api/v1/analytics/equity                       # Equity metrics by area
GET /api/v1/analytics/export?format=csv|json       # Data export
```

All analytics endpoints require staff or admin role.
