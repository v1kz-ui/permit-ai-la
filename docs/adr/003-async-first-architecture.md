# ADR-003: Async-First Architecture

## Status
Accepted

## Context
Multiple I/O-bound operations: external API calls (Socrata, ZIMAS, PCIS, Claude), database queries, Redis operations, S3 uploads. WebSocket support needed for real-time dashboard.

## Decision
- FastAPI with async endpoints throughout
- SQLAlchemy 2.0 async with asyncpg driver
- redis.asyncio for cache and pub/sub
- httpx.AsyncClient for external API calls
- Airflow for scheduled data pipelines (separate process)

## Consequences
- Single API process handles hundreds of concurrent connections
- WebSocket support native in FastAPI
- All database and external calls are non-blocking
- Must use async test fixtures (pytest-asyncio)
