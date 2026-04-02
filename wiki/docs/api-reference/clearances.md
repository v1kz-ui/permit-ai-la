---
sidebar_position: 3
title: Clearances
---

# Clearances API

Manage departmental clearances for projects.

## Create Clearance

```
POST /api/v1/clearances
```

**Auth:** Staff/admin only.

```json
{
  "project_id": "uuid",
  "department": "ladbs",
  "clearance_type": "Building Plan Check",
  "status": "not_started"
}
```

## List Clearances

```
GET /api/v1/clearances?project_id={uuid}
```

Returns all clearances for the specified project, ordered by department and type.

## Update Clearance Status

```
PATCH /api/v1/clearances/{clearance_id}
```

```json
{
  "status": "approved"
}
```

Emits a `clearance_changed` event via Redis pub/sub for real-time updates. Automatically sets `completed_date` when status is `approved` or `not_applicable`.

## Department Values

```
ladbs | dcp | boe | lafd | ladwp | lasan | lahd | dot | cultural_affairs | urban_forestry | la_county
```

## Status Values

```
not_started | in_review | approved | conditional | denied | not_applicable
```
