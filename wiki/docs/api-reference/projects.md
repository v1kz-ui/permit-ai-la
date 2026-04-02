---
sidebar_position: 2
title: Projects
---

# Projects API

CRUD operations for fire rebuild permit projects.

## Create Project

```
POST /api/v1/projects
```

Creates a new project and auto-links to a parcel if found by address. Automatically generates baseline clearances.

**Request Body:**
```json
{
  "address": "123 Fire Rd, Los Angeles, CA 90001",
  "description": "Single-family home rebuild after Palisades fire",
  "original_sqft": 2000,
  "proposed_sqft": 2200,
  "stories": 2
}
```

**Response:** `201 Created` with full `ProjectResponse` including parcel data and overlay flags.

## List Projects

```
GET /api/v1/projects?status=in_review&pathway=eo1_like_for_like&page=1&size=20
```

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by project status |
| `pathway` | string | Filter by pathway |
| `page` | integer | Page number (default: 1) |
| `size` | integer | Items per page (default: 20, max: 100) |

Homeowners see only their projects. Staff/admin see all.

## Get Project Detail

```
GET /api/v1/projects/{project_id}
```

Returns full project with clearances, inspections, and documents.

## Update Project

```
PATCH /api/v1/projects/{project_id}
```

Partial update. Only provided fields are changed.

```json
{
  "proposed_sqft": 2500,
  "stories": 2
}
```
