---
sidebar_position: 1
title: API Overview
---

# API Reference

Base URL: `http://localhost:8000/api/v1` (development) | `https://api.permitai.la/api/v1` (production)

## Authentication

All endpoints (except `/health` and `/monitoring`) require an Angeleno OAuth bearer token:

```
Authorization: Bearer <angeleno_token>
```

**Development mode:** Set `MOCK_AUTH=true` to bypass authentication with a mock user.

## Roles & Permissions

| Role | Access |
|------|--------|
| `homeowner` | Own projects, clearances, documents, chat |
| `contractor` | Same as homeowner |
| `architect` | Same as homeowner |
| `staff` | All projects, analytics, reports, staff dashboard |
| `admin` | Everything + user management, audit logs, cache control |

## Rate Limiting

- **Chat:** 20 messages/hour per user (Redis-backed, fail-open)
- **General API:** Configurable via middleware (default: generous limits)

## Error Format

Errors follow RFC 7807 Problem Details:

```json
{
  "type": "validation_error",
  "title": "Invalid Input",
  "status": 422,
  "detail": "proposed_sqft must be greater than 0",
  "instance": "/api/v1/projects"
}
```

## Pagination

List endpoints support pagination:

```
GET /api/v1/projects?page=2&size=20
```

Response includes:
```json
{
  "items": [...],
  "total": 150,
  "page": 2,
  "size": 20,
  "pages": 8
}
```

## OpenAPI Docs

Interactive API documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
