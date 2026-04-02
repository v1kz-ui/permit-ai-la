---
sidebar_position: 6
title: Analytics & Reports
---

# Analytics & Reports API

Performance metrics, trend data, and report generation. **Staff/admin only.**

## Pipeline Metrics

```
GET /api/v1/analytics/pipeline
```

Returns completion rates, average days to issue, and bottleneck frequency by department.

## Geographic Heatmap

```
GET /api/v1/analytics/geographic
```

Returns project density data for heatmap visualization.

## Department Performance

```
GET /api/v1/analytics/department/{department}
```

Returns detailed metrics for a specific department.

## Trend Data

```
GET /api/v1/analytics/trends?metric=permits_issued&period=30
```

| Param | Values |
|-------|--------|
| `metric` | `permits_issued`, `clearances_completed`, `bottlenecks` |
| `period` | `7`, `30`, `90` (days) |

## Equity Metrics

```
GET /api/v1/analytics/equity
```

Returns per-area breakdown of project counts and processing times to identify disparities.

## Data Export

```
GET /api/v1/analytics/export?format=csv
```

Downloads analytics data as CSV or JSON. Includes formula injection protection for CSV exports.

## Reports

```
GET  /api/v1/reports/weekly?week=2026-03-24        # Weekly summary
GET  /api/v1/reports/department/{dept}?start=&end=  # Department workload
GET  /api/v1/reports/project/{id}                   # Project status report
POST /api/v1/reports/schedule                       # Schedule recurring reports
```
