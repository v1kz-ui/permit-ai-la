---
sidebar_position: 2
title: Audit Logging
---

# Audit Logging

Every data change in PermitAI is recorded in an immutable audit trail.

## How It Works

The `AuditMiddleware` intercepts all create, update, and delete operations and records them in the `audit_log` table.

Each audit entry captures:
- **Who:** User ID
- **What:** Entity type (table name), entity ID, action (create/update/delete)
- **When:** Timestamp
- **How:** IP address, user agent
- **Changes:** JSONB before/after snapshot of changed fields

## Immutability

Audit log rows are **never updated or deleted**. This provides a complete, tamper-evident history of all system changes for compliance purposes.

## Dashboard UI

### Admin Panel (`/admin`)
Shows a preview of recent audit entries with:
- Timestamp
- Action (INSERT/UPDATE/DELETE)
- Table name
- Record ID

### Full Audit Log (`/admin/audit`)
Comprehensive audit viewer with:
- **Date range filters** (start/end)
- **Table filter** dropdown
- **User ID search**
- **Export** to JSON or CSV
- **Expandable rows** showing before/after JSON diffs side-by-side

## API Endpoints

```
GET /api/v1/admin/audit                   # Paginated audit log with filters
GET /api/v1/admin/audit/{record_id}       # Full audit trail for a specific record
```

Both endpoints require admin role.

## Tracked Entities

All core entities are audited:
- Users (role changes, profile updates)
- Projects (status changes, field updates)
- Clearances (status transitions)
- Inspections (scheduling, results)
- Documents (uploads, deletions)
