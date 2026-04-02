---
sidebar_position: 2
title: Backend
---

# Backend Architecture

The backend is a FastAPI application with a layered architecture.

## Application Startup

The `create_app()` factory in `backend/app/main.py`:

1. Creates the FastAPI instance (title: "PermitAI LA", version: "0.1.0")
2. Registers middleware stack (in execution order):
   - Error handler -- catches unhandled exceptions
   - Rate limiter -- Redis-backed request throttling
   - Request logger -- structured logging with `structlog`
   - Audit logger -- immutable change tracking
   - Security headers -- HSTS, X-Frame-Options, CSP
   - Monitoring -- Prometheus-compatible metrics
3. Mounts the v1 API router at `/api/v1`
4. On startup: verifies DB + Redis connectivity, warms caches, initializes Sentry

## Middleware Stack

| Middleware | Purpose | File |
|-----------|---------|------|
| `ErrorHandlerMiddleware` | Global error handling + sanitization | `core/middleware.py` |
| `RateLimitMiddleware` | Redis-backed rate limiting (fail-open) | `core/middleware.py` |
| `RequestLoggingMiddleware` | Structured request/response logging | `core/middleware.py` |
| `AuditMiddleware` | Immutable audit log for data changes | `core/middleware.py` |
| `SecurityHeadersMiddleware` | HSTS, X-Frame-Options, CSP headers | `core/middleware.py` |
| `MonitoringMiddleware` | Request count, duration, status metrics | `core/middleware.py` |

## Service Layer

Business logic lives in `backend/app/services/`:

| Service | Purpose |
|---------|---------|
| `clearance_service.py` | Clearance CRUD, auto-generation from parcel flags, status events |
| `chat_service.py` | RAG chat with Claude, prompt injection filtering, rate limiting |
| `conflict_service.py` | Detects conflicting clearance requirements |
| `notification_service.py` | Push, SMS, email notification dispatch |

## AI / ML Layer

Located in `backend/app/ai/`:

| Module | Purpose |
|--------|---------|
| `pathfinder/rules_engine.py` | Deterministic pathway evaluation (EO1/EO8/Standard) |
| `pathfinder/claude_reasoner.py` | Claude API for edge-case reasoning |
| `pathfinder/standard_plan_matcher.py` | Pre-approved construction plan finder |
| `predictor/bottleneck_model.py` | XGBoost bottleneck prediction with heuristic fallback |

## API Routes

All routes are registered under `/api/v1`. See [API Reference](/api-reference/overview) for full endpoint documentation.

| Router | Prefix | Auth Required |
|--------|--------|--------------|
| health | `/health` | No |
| projects | `/projects` | Yes |
| clearances | `/clearances` | Yes |
| parcels | `/parcels` | Yes |
| pathfinder | `/pathfinder` | Yes |
| chat | `/chat` | Yes (20 msg/hr) |
| documents | `/documents` | Yes |
| inspections | `/inspections` | Yes |
| analytics | `/analytics` | Staff/Admin |
| reports | `/reports` | Staff/Admin |
| staff | `/staff` | Staff/Admin |
| admin | `/admin` | Admin |
| compliance | `/compliance` | Yes |
| impact | `/impact` | Yes |
| users | `/users` | Yes |
| websocket | `/ws` | Yes |
| monitoring | `/monitoring` | No |

## Configuration

All settings are managed via Pydantic `BaseSettings` in `backend/app/config.py`, loading from environment variables. See [Environment Variables](/getting-started/environment-variables).

## Logging

Uses `structlog` for structured JSON logging in production, with human-readable console output in development. Every request is logged with method, path, status code, and duration.
