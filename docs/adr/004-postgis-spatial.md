# ADR-004: PostGIS for All Spatial Operations

## Status
Accepted

## Context
Every permit lookup involves geography: parcel geometry, zone overlays, coastal boundaries, hillside areas, fire severity zones. Need spatial queries like "find parcel containing this lat/lng" and "which overlays apply to this APN."

## Decision
Use PostgreSQL 16 + PostGIS 3.4 with GeoAlchemy2 for all spatial operations. Store parcel geometries as MULTIPOLYGON (SRID 4326) with GIST indexes.

## Consequences
- Spatial queries (ST_Contains, ST_Intersects) run in DB with proper indexing
- No external geocoding service dependency for parcel lookups
- ZIMAS data cached locally with geometry for offline capability
- Requires PostGIS extension in all environments (dev, test, staging, prod)
