---
sidebar_position: 7
title: Admin
---

# Admin API

System administration endpoints. **Admin role required.**

## User Management

```
GET   /api/v1/admin/users                    # List all users (paginated)
PATCH /api/v1/admin/users/{user_id}/role     # Change user role
```

Roles: `homeowner`, `contractor`, `architect`, `staff`, `admin`

## Audit Log

```
GET /api/v1/admin/audit                      # System audit log (filterable)
GET /api/v1/admin/audit/{record_id}          # Audit trail for specific record
```

Query parameters:
- `start_date`, `end_date` -- Date range filter
- `table` -- Filter by entity table
- `user_id` -- Filter by user

## System Health

```
GET /api/v1/admin/system-health              # Extended health check
```

Returns database status, Redis status, queue depth, active project count.

## Cache Management

```
DELETE /api/v1/admin/cache                   # Clear all Redis caches
```

## Bulk Operations

```
POST /api/v1/admin/bulk-update-clearances    # Bulk status updates
```

## Staff Dashboard

```
GET /api/v1/staff/dashboard/stats            # KPI stats (active projects, pending clearances, etc.)
GET /api/v1/staff/dashboard/department-workload  # Per-department clearance workload
GET /api/v1/staff/dashboard/bottlenecks      # Active bottleneck list
GET /api/v1/staff/kanban?department=ladbs     # Kanban board data
GET /api/v1/staff/projects                   # All projects (staff/admin)
```
