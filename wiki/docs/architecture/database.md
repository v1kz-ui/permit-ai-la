---
sidebar_position: 4
title: Database
---

# Database Schema

PostgreSQL 16 with PostGIS extension for geospatial queries. Managed via SQLAlchemy 2.0 (async) with Alembic migrations.

## Entity Relationship Diagram

```
┌──────────┐     ┌────────────┐     ┌─────────────┐
│   User   │────<│  Project   │────<│  Clearance  │
│          │     │            │     │             │
│ id (PK)  │     │ id (PK)    │     │ id (PK)     │
│ email    │     │ owner_id   │     │ project_id  │
│ name     │     │ address    │     │ department  │
│ role     │     │ apn        │     │ status      │
│ language │     │ pathway    │     │ is_bottleneck│
└──────────┘     │ status     │     └─────────────┘
                 └──────┬─────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
   ┌──────▼─────┐ ┌────▼──────┐ ┌───▼────────┐
   │ Inspection │ │ Document  │ │Notification│
   │            │ │           │ │            │
   │ id (PK)   │ │ id (PK)   │ │ id (PK)    │
   │ project_id│ │ project_id│ │ user_id    │
   │ type      │ │ s3_key    │ │ type       │
   │ status    │ │ filename  │ │ channel    │
   └────────────┘ └───────────┘ └────────────┘

┌──────────┐     ┌────────────┐
│  Parcel  │     │  AuditLog  │
│          │     │            │
│ apn (PK) │     │ id (PK)    │
│ geom     │     │ user_id    │
│ zone     │     │ entity_type│
│ overlays │     │ action     │
└──────────┘     │ changes    │
                 └────────────┘
```

## Core Entities

### User
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `email` | String(255), unique | User email |
| `name` | String(255) | Display name |
| `role` | Enum | `homeowner`, `contractor`, `architect`, `staff`, `admin` |
| `language` | Enum | `en`, `es`, `ko`, `zh`, `tl` |
| `angeleno_id` | String(100), unique | LA Angeleno OAuth ID |
| `firebase_token` | Text | Push notification token |

### Project
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `owner_id` | UUID (FK -> User) | Project owner |
| `address` | String(500) | Property address |
| `apn` | String(20), indexed | Assessor Parcel Number |
| `ladbs_permit_number` | String(20), unique | LADBS permit number |
| `pathway` | Enum | `eo1_like_for_like`, `eo8_expanded`, `standard`, `self_certification`, `unknown` |
| `status` | Enum | `intake` through `closed` (10 statuses) |
| `original_sqft` | Integer | Original building square footage |
| `proposed_sqft` | Integer | Proposed rebuild square footage |
| `stories` | Integer | Number of stories |
| `is_coastal_zone` | Boolean | Coastal overlay flag |
| `is_hillside` | Boolean | Hillside overlay flag |
| `is_very_high_fire_severity` | Boolean | VHFSZ overlay flag |
| `is_historic` | Boolean | Historic property flag |
| `predicted_days_to_issue` | Integer | AI-predicted days to permit |

### Clearance
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `project_id` | UUID (FK -> Project) | Associated project |
| `department` | Enum | `ladbs`, `dcp`, `boe`, `lafd`, `ladwp`, `lasan`, `lahd`, `dot`, `cultural_affairs`, `urban_forestry`, `la_county` |
| `clearance_type` | String(100) | Type of clearance |
| `status` | Enum | `not_started`, `in_review`, `approved`, `conditional`, `denied`, `not_applicable` |
| `is_bottleneck` | Boolean | Flagged by ML model |
| `predicted_days` | Integer | Predicted days to completion |
| `submitted_date` | DateTime | When submitted |
| `completed_date` | DateTime | When completed |

Composite index on `(project_id, department)`.

### Parcel (Geospatial)
| Column | Type | Description |
|--------|------|-------------|
| `apn` | String(20) (PK) | Assessor Parcel Number |
| `geom` | PostGIS MULTIPOLYGON (SRID 4326) | Parcel geometry |
| `zone_class` | String(20) | Zoning classification |
| `lot_area_sqft` | Float | Lot area |
| `council_district` | Integer | LA Council district |
| Overlay flags | Boolean columns | `is_coastal_zone`, `is_hillside`, `is_very_high_fire_severity`, `is_flood_zone`, `is_geological_hazard`, `is_historic`, `has_hpoz` |

Spatial index on `geom` column for PostGIS queries.

### Inspection
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `project_id` | UUID (FK -> Project) | Associated project |
| `inspection_type` | String(50) | Type (foundation, framing, electrical, etc.) |
| `status` | Enum | `scheduled`, `passed`, `failed`, `cancelled`, `no_show` |
| `scheduled_date` | DateTime | Scheduled inspection date |
| `inspector_name` | String(100) | Assigned inspector |
| `failure_reasons` | ARRAY(String) | Reasons for failure |

### Document
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `project_id` | UUID (FK -> Project) | Associated project |
| `s3_key` | String(500) | S3 object key |
| `filename` | String(255) | Original filename |
| `content_type` | String(100) | MIME type |
| `file_size_bytes` | Integer | File size |
| `document_type` | Enum | `permit_application`, `architectural_plan`, `structural_plan`, etc. |

### AuditLog
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `user_id` | UUID (FK -> User) | Who made the change |
| `entity_type` | String(50) | Table name |
| `entity_id` | String(50) | Record ID |
| `action` | Enum | `create`, `update`, `delete` |
| `changes` | JSONB | Before/after snapshot |

Immutable -- rows are never updated or deleted.

## Migrations

Managed with Alembic. Migration files are in `backend/alembic/versions/`.

```bash
# Run pending migrations
make migrate

# Create a new migration
make migration msg="add new column"
```

## Caching Strategy

| Data | TTL | Purpose |
|------|-----|---------|
| Parcel lookups | 24 hours | Parcel data changes rarely |
| Map GeoJSON | 5 minutes | Dashboard map data |
| Pipeline metrics | 1 minute | Dashboard KPI cards |
| Rate limit counters | 1 hour | Chat rate limiting |
