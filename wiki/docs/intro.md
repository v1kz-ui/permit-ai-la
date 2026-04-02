---
slug: /
sidebar_position: 1
title: Introduction
---

# PermitAI LA

**AI-powered fire rebuild permit tracking and acceleration for Los Angeles.**

PermitAI LA helps homeowners, contractors, and city staff navigate the complex multi-department permitting process after wildfires. It combines deterministic rules engines with Claude AI to determine optimal permit pathways, predict processing bottlenecks, and coordinate clearances across 10 LA city departments.

## What It Does

- **PathfinderAI** -- Determines the fastest permit pathway (EO1 Like-for-Like, EO8 Expanded, or Standard) using a rules engine with Claude AI for edge cases
- **Multi-Department Clearance Tracking** -- Real-time status tracking across LADBS, DCP, LAFD, BOE, LADWP, LASAN, LAHD, DOT, Cultural Affairs, and Urban Forestry
- **Bottleneck Prediction** -- XGBoost ML model predicts processing delays and flags at-risk clearances
- **AI Chat Assistant** -- Claude-powered RAG chatbot answering homeowner questions about the permit process
- **What-If Scenario Analysis** -- Compare timelines across EO1, EO8, and Standard pathways
- **Staff Kanban Board** -- Drag-and-drop clearance management with 5-second undo
- **Analytics & Equity Dashboard** -- Department performance, geographic trends, equity metrics
- **Document Management** -- Upload/download permits, plans, and reports via S3
- **Inspector Routing** -- Geographic clustering for optimal inspection scheduling
- **Compliance Checker** -- Validates clearance sequencing and pathway rules
- **Impact Dashboard** -- Public-facing outcomes and metrics
- **Multi-Language Support** -- English, Spanish, Korean, Chinese, Tagalog
- **Mobile App** -- React Native (iOS/Android/Web)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12+), SQLAlchemy 2.0, async/await throughout |
| Database | PostgreSQL 16 + PostGIS for geospatial queries |
| Cache | Redis (caching, rate limiting, pub/sub) |
| Frontend | Next.js 14, React 18, Recharts, Mapbox GL, Tailwind CSS |
| Mobile | React Native + Expo |
| AI/ML | Claude API (Anthropic), XGBoost, Prophet, SpaCy |
| Pipeline | Apache Airflow + Celery for data ingestion |
| Cloud | AWS (ECS Fargate, RDS, S3, ElastiCache) |

## Data Integrations

| Source | Method | Purpose |
|--------|--------|---------|
| LADBS Open Data | Socrata REST API | Permit records (every 15 min) |
| ZIMAS / GeoHub | Esri ArcGIS REST API | Parcel zoning and overlays (daily) |
| PCIS | Web scraper | Clearance status (3x daily) |
| ePlanLA | OAuth API | Application status (hourly) |
| LAFD FIMS 2.0 | Vendor API | Fire clearances (hourly) |

## Quick Links

- [Quickstart Guide](/getting-started/quickstart) -- Get the dev environment running
- [Architecture Overview](/architecture/overview) -- System design and tech stack
- [API Reference](/api-reference/overview) -- All REST endpoints
- [LA Permitting Guide](/la-permitting/departments) -- Understanding LA's permit process
