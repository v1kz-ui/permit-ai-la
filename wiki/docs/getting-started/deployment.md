---
sidebar_position: 3
title: Deployment
---

# Deployment

PermitAI LA is designed to deploy on AWS infrastructure.

## Architecture

```
                    ┌─────────────┐
                    │  CloudFront │
                    │   (CDN)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
      ┌───────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
      │   Dashboard  │ │ API  │ │   Mobile    │
      │   (Vercel/   │ │ ECS  │ │   (Expo)    │
      │  CloudFront) │ │Fargate│ │             │
      └──────────────┘ └──┬───┘ └─────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
      ┌───────▼──┐  ┌────▼────┐  ┌──▼──────┐
      │   RDS    │  │  Elasti │  │   S3    │
      │PostgreSQL│  │  Cache  │  │Documents│
      │ +PostGIS │  │ (Redis) │  │         │
      └──────────┘  └─────────┘  └─────────┘
```

## AWS Services

| Service | Purpose | Configuration |
|---------|---------|--------------|
| ECS Fargate | API server (FastAPI) | 2 vCPU, 4 GB RAM, auto-scaling |
| RDS | PostgreSQL 16 + PostGIS | db.r6g.large, Multi-AZ |
| ElastiCache | Redis 7 | cache.r6g.large |
| S3 | Document storage | Versioning enabled, lifecycle rules |
| CloudFront | CDN for dashboard + S3 | HTTPS, gzip compression |
| Secrets Manager | API keys, OAuth secrets | Rotation enabled |

## Deployment Steps

### 1. Infrastructure (Terraform/CDK)

Provision RDS, ElastiCache, ECS cluster, S3 buckets, and networking.

### 2. Database Migration

```bash
alembic upgrade head
```

### 3. Build & Deploy API

```bash
docker build -t permitai-api ./backend
# Push to ECR, update ECS service
```

### 4. Build & Deploy Dashboard

```bash
cd dashboard
npm run build
# Deploy to Vercel or upload to S3 + CloudFront
```

### 5. Data Pipeline (Optional)

Start Airflow for automated data ingestion:

```bash
docker compose --profile airflow up -d
```

## Health Monitoring

- **Health endpoint:** `GET /api/v1/health` -- checks DB and Redis connectivity
- **Prometheus metrics:** `GET /api/v1/monitoring/metrics`
- **Sentry:** Set `SENTRY_DSN` for error tracking
