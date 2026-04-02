---
sidebar_position: 5
title: Data Pipeline
---

# Data Pipeline

PermitAI LA ingests permit data from multiple LA city systems using Apache Airflow for orchestration.

## Data Sources

| Source | Client | Frequency | Purpose |
|--------|--------|-----------|---------|
| LADBS Open Data | `SocrataClient` | Every 15 min | Permit records, application status |
| ZIMAS / GeoHub | `ZIMASClient` | Daily | Parcel geometry, zoning, overlay flags |
| PCIS | `PCISScraper` | 3x daily | Clearance status updates |
| ePlanLA | `ePlanLAClient` | Hourly | Application status (OAuth) |
| LAFD FIMS 2.0 | `FIMSClient` | Hourly | Fire/life safety clearance status |

## Ingestion Pipeline

```
Data Source → Client (fetch) → Transformer (normalize) → Loader (upsert to DB)
                                                              │
                                                              ▼
                                                     PostgreSQL + Redis
                                                     (cache invalidation)
```

### Socrata Client
- Fetches LADBS permit records from LA Open Data portal
- Async HTTP with pagination and retry logic
- Handles rate limiting and API token authentication
- Dataset ID: `hbkd-qubn`

### ZIMAS Client
- Fetches parcel geometry and zoning from Esri ArcGIS REST API
- Returns: zone class, overlays (coastal, hillside, fire, historic, flood), lot dimensions
- Results cached 24 hours per parcel in Redis

### PCIS Scraper
- Web scraper for Plan Check and Inspection System
- Falls back to scraping when API is unavailable
- Extracts clearance case numbers and status

### ePlanLA Client
- OAuth-authenticated REST API
- Tracks application submission and plan check status
- Supports self-reported status updates

### FIMS Client
- Vendor API for LA Fire Department
- Retrieves fire/life safety clearance status
- Tracks brush clearance compliance

## Airflow DAGs

Start Airflow with:

```bash
docker compose --profile airflow up -d
```

Access the Airflow UI at `http://localhost:8080` (admin/admin).

DAG files are in `backend/airflow/dags/`.

## Data Transformation

Each data source has a transformer that normalizes external data into the internal schema:
- Standardizes address formats
- Maps external status codes to internal enums
- Enriches parcels with overlay flags from ZIMAS
- Deduplicates records by APN or permit number
