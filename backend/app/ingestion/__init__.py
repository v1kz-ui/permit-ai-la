"""Data ingestion pipeline for PermitAI LA.

Submodules:
    - socrata_client: LADBS Open Data API client
    - transformers: Data normalization and transformation functions
    - loaders: Database upsert and dead-letter handling
    - zimas_client: ZIMAS / GeoHub ArcGIS REST client
    - pcis_scraper: PCIS clearance scraper (fallback)
"""
