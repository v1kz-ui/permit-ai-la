---
sidebar_position: 1
title: Architecture Overview
---

# Architecture Overview

PermitAI LA is a full-stack monorepo with four main components.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  Mobile   │  │  Dashboard   │  │  External Systems   │   │
│  │  (Expo)   │  │  (Next.js)   │  │  (LADBS, ZIMAS...)  │   │
│  └─────┬─────┘  └──────┬───────┘  └──────────┬──────────┘   │
└────────┼───────────────┼─────────────────────┼───────────────┘
         │               │                     │
         └───────┬───────┘                     │
                 ▼                             │
┌────────────────────────────────┐             │
│        FastAPI Backend         │◄────────────┘
│  ┌──────────┐ ┌─────────────┐ │
│  │ REST API │ │  WebSocket  │ │
│  │  (v1)    │ │  (realtime) │ │
│  └──────────┘ └─────────────┘ │
│  ┌──────────────────────────┐ │
│  │      Middleware Stack    │ │
│  │  Auth │ Audit │ Rate     │ │
│  │  Limit│ Log   │ Security │ │
│  └──────────────────────────┘ │
│  ┌──────────────────────────┐ │
│  │     Service Layer        │ │
│  │ Projects│Clearances│Chat │ │
│  └──────────────────────────┘ │
│  ┌──────────────────────────┐ │
│  │       AI / ML Layer      │ │
│  │ PathfinderAI │ Bottleneck│ │
│  │ Rules Engine │ Predictor │ │
│  │ Claude       │ XGBoost   │ │
│  └──────────────────────────┘ │
└──────┬──────────────┬─────────┘
       │              │
  ┌────▼────┐   ┌─────▼────┐   ┌─────────┐
  │PostgreSQL│   │  Redis   │   │   S3    │
  │ +PostGIS │   │          │   │  (docs) │
  └──────────┘   └──────────┘   └─────────┘
```

## Repository Structure

```
Permit-AI-for-LA/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/v1/           # Route handlers
│   │   ├── ai/               # PathfinderAI, bottleneck predictor
│   │   ├── core/             # Config, events, middleware
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic layer
│   ├── alembic/              # Database migrations
│   ├── scripts/              # Data generation, seeding
│   └── tests/                # pytest test suite
├── dashboard/                # Next.js 14 staff dashboard
│   └── src/
│       ├── app/              # Page routes (App Router)
│       ├── components/       # Reusable UI components
│       └── lib/              # API client, utilities
├── mobile/                   # React Native + Expo
├── shared/                   # Shared types and config
│   ├── types.ts              # TypeScript type definitions
│   └── clearance_types.json  # Department/clearance taxonomy
├── docs/                     # ADRs, runbooks, API reference
├── wiki/                     # This documentation site (Docusaurus)
├── docker-compose.yml        # Infrastructure services
├── Makefile                  # Development commands
└── .env.example              # Environment variable template
```

## Design Principles

1. **Rules first, AI second** -- The deterministic rules engine has absolute veto power over Claude AI recommendations. AI is called only for edge cases.

2. **Async throughout** -- Full async/await stack from FastAPI to SQLAlchemy to Redis. No blocking I/O in the request path.

3. **Fail-open gracefully** -- If Redis is down, rate limiting is skipped. If Claude API is unavailable, the rules engine still works. Mock data fallback in the dashboard.

4. **Audit everything** -- Every create, update, and delete operation is logged in an immutable audit trail with before/after snapshots.

5. **Multi-department coordination** -- The system models LA's real permit workflow: clearances from 10 departments must be coordinated, with some requiring sequential ordering.
