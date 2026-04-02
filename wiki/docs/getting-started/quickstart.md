---
sidebar_position: 1
title: Quickstart
---

# Quickstart

Get PermitAI LA running locally in under 5 minutes.

## Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Git

## 1. Clone & Install

```bash
git clone https://github.com/SongNiviworksmo/Permit-AI-for-LA.git
cd Permit-AI-for-LA
make install
```

This installs:
- Backend Python dependencies (FastAPI, SQLAlchemy, etc.)
- Dashboard npm packages (Next.js, React)
- Mobile npm packages (Expo, React Native)

## 2. Start Infrastructure

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** with PostGIS on port `5432`
- **Redis 7** on port `6379`

## 3. Configure Environment

```bash
cp .env.example .env
```

For local development, the defaults work out of the box with `MOCK_AUTH=true`. See [Environment Variables](/getting-started/environment-variables) for all options.

## 4. Run Database Migrations

```bash
make migrate
```

This runs Alembic migrations to create all tables (users, projects, parcels, clearances, inspections, documents, notifications, audit_log).

## 5. Seed Data (Optional)

```bash
make seed
```

Populates reference data including parcel records and sample projects.

## 6. Start the API

```bash
make dev
```

The FastAPI server starts on `http://localhost:8000` with hot-reload enabled.

- API docs: `http://localhost:8000/docs` (Swagger UI)
- Health check: `http://localhost:8000/api/v1/health`

## 7. Start the Dashboard

```bash
make dashboard
```

The Next.js dashboard starts on `http://localhost:3000`.

## 8. Start Mobile (Optional)

```bash
make mobile
```

Expo dev server starts for iOS/Android/Web.

## Full Stack (All Services)

To start everything including Airflow and Mailhog:

```bash
make dev-full
```

## Available Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start API with PostgreSQL + Redis |
| `make dev-full` | Start all services including Airflow + Mail |
| `make test` | Run pytest with coverage |
| `make lint` | Run ruff + mypy checks |
| `make lint-fix` | Auto-fix linting issues |
| `make migrate` | Run Alembic migrations |
| `make dashboard` | Start Next.js dashboard |
| `make mobile` | Start Expo mobile app |
| `make down` | Stop all Docker services |
| `make clean` | Full teardown including volumes |
