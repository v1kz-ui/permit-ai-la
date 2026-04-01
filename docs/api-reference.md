# PermitAI LA - API Reference

Base URL: `https://api.permitai.la/api/v1` (production)
Local: `http://localhost:8000/api/v1`

## Authentication
All endpoints (except /health) require Angeleno OAuth bearer token.
Dev mode: set `MOCK_AUTH=true` for automatic mock user.

```
Authorization: Bearer <angeleno_token>
```

---

## Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check (DB + Redis) |

## Projects
| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects` | Create project from address |
| GET | `/projects` | List user's projects (paginated) |
| GET | `/projects/{id}` | Get project with clearances/inspections |
| PATCH | `/projects/{id}` | Update project details |

## Clearances
| Method | Path | Description |
|--------|------|-------------|
| POST | `/clearances` | Create clearance (staff only) |
| GET | `/clearances?project_id=` | List clearances for project |
| PATCH | `/clearances/{id}` | Update clearance status |

## PathfinderAI
| Method | Path | Description |
|--------|------|-------------|
| POST | `/pathfinder/analyze/{project_id}` | Full AI analysis pipeline |
| POST | `/pathfinder/quick-analysis` | Address-only quick analysis |
| GET | `/pathfinder/conflicts/{project_id}` | Detect clearance conflicts |
| GET | `/pathfinder/timeline/{project_id}` | Predict project timeline |

## Parcels
| Method | Path | Description |
|--------|------|-------------|
| GET | `/parcels/{apn}` | Get parcel by APN (cached) |
| GET | `/parcels/lookup/by-coordinates?lat=&lng=` | Spatial parcel lookup |

## Users
| Method | Path | Description |
|--------|------|-------------|
| POST | `/users` | Register new user |
| GET | `/users/me` | Get current user profile |
| PATCH | `/users/me` | Update profile |
| GET | `/users/me/notification-preferences` | Get notification prefs |
| PUT | `/users/me/notification-preferences` | Update notification prefs |

## Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/{project_id}` | Send message to AI assistant |

## Documents
| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/upload/{project_id}` | Upload document (multipart) |
| GET | `/documents/{project_id}` | List project documents |
| GET | `/documents/{document_id}/download` | Get download URL |
| DELETE | `/documents/{document_id}` | Delete document |

## Staff Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/staff/dashboard/stats` | Dashboard summary stats |
| GET | `/staff/department-workload` | Per-department workload |
| GET | `/staff/bottlenecks` | Active bottlenecks |
| GET | `/staff/kanban?department=` | Kanban board data |
| GET | `/staff/projects` | All projects (staff only) |

## Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/pipeline` | Pipeline metrics |
| GET | `/analytics/geographic` | Geographic heatmap data |
| GET | `/analytics/department/{dept}` | Department performance |
| GET | `/analytics/trends?metric=&period=` | Trend data |
| GET | `/analytics/equity` | Equity metrics |
| GET | `/analytics/export?format=` | Export analytics (csv/json) |

## Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports/weekly?week=` | Weekly summary report |
| GET | `/reports/department/{dept}` | Department report |
| GET | `/reports/project/{id}` | Project report |
| POST | `/reports/schedule` | Schedule recurring report |

## Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/users` | List all users |
| PATCH | `/admin/users/{id}/role` | Change user role |
| GET | `/admin/audit` | System audit log |
| GET | `/admin/audit/{record_id}` | Record audit trail |
| POST | `/admin/bulk-update-clearances` | Bulk update clearances |
| GET | `/admin/system-health` | Extended health check |
| DELETE | `/admin/cache` | Clear cache |

## Compliance
| Method | Path | Description |
|--------|------|-------------|
| GET | `/compliance/check/{project_id}` | Full compliance check |
| GET | `/compliance/requirements/{pathway}` | Pathway requirements |
| POST | `/compliance/validate-sequence/{id}` | Validate clearance order |

## Monitoring
| Method | Path | Description |
|--------|------|-------------|
| GET | `/monitoring/metrics` | Prometheus metrics |
| GET | `/monitoring/health/detailed` | Extended health |
| GET | `/monitoring/health/ready` | Readiness probe |
| GET | `/monitoring/health/live` | Liveness probe |

## WebSocket
| Protocol | Path | Description |
|----------|------|-------------|
| WS | `/ws/{project_id}?token=` | Real-time project updates |

---

## Common Response Formats

### Paginated Response
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

### Error Response (RFC 7807)
```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Project not found",
  "instance": "/api/v1/projects/abc-123"
}
```
