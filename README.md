# PermitAI LA

AI-powered platform to accelerate fire rebuilding permit processes in Los Angeles. Provides homeowners and city staff with intelligent real-time tracking, predictive analytics, and automated regulatory guidance.

## Architecture

- **Backend**: Python FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16 + PostGIS
- **Data Pipelines**: Apache Airflow + Celery
- **AI/ML**: Claude API + XGBoost + Prophet + SpaCy
- **Staff Dashboard**: Next.js + React + Recharts + Mapbox GL
- **Mobile App**: React Native + Expo (iOS/Android/Web)
- **Infrastructure**: AWS (ECS Fargate + RDS + ElastiCache + S3)

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20 LTS
- Docker Desktop

### Setup

```bash
# Clone and install
cp .env.example .env
make install

# Start services (PostgreSQL + Redis)
make dev

# In another terminal, run migrations and seed data
make migrate
make seed
```

### Development

```bash
make dev          # Start API server + core services
make dev-full     # Start everything including Airflow
make test         # Run tests with coverage
make lint         # Run linters
make dashboard    # Start Next.js dashboard
make mobile       # Start Expo mobile app
```

## Project Structure

```
permitai-la/
├── backend/          # FastAPI backend + data pipelines
├── dashboard/        # Next.js staff dashboard
├── mobile/           # React Native + Expo mobile app
├── infrastructure/   # Terraform + Dockerfiles
├── shared/           # Cross-platform types + enums
├── rules/            # Versioned regulatory rule definitions
└── docs/             # Architecture, API docs, ADRs
```

## Data Sources

| Source | Method | Frequency |
|--------|--------|-----------|
| LADBS Open Data | Socrata REST API | Every 15 min |
| ZIMAS / GeoHub | Esri ArcGIS REST API | Daily cache |
| PCIS Clearances | Web scraper (fallback) | 3x daily |
| ePlanLA | OAuth API / self-report | Hourly |
| LAFD FIMS 2.0 | Vendor API | Hourly |

## License

Proprietary - City of Los Angeles
