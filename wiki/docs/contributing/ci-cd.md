---
sidebar_position: 2
title: CI/CD
---

# CI/CD Pipeline

## GitHub Actions

The project uses GitHub Actions for continuous integration.

### Workflows

Located in `.github/workflows/`:

#### Lint & Test
Runs on every push and pull request:
1. **Lint:** `ruff check`, `ruff format --check`, `mypy`
2. **Test:** `pytest` with coverage report
3. **Build:** `npm run build` for dashboard

#### Deploy (Production)
Triggered on merge to `main`:
1. Build Docker image for backend
2. Push to ECR
3. Update ECS Fargate service
4. Run database migrations
5. Build and deploy dashboard to CloudFront/Vercel

## Local CI Check

Run the same checks locally before pushing:

```bash
make lint    # Ruff + mypy
make test    # pytest with coverage
cd dashboard && npm run build  # Frontend build check
```

## Docker

### Build Backend Image

```bash
docker build -t permitai-api ./backend
```

### Infrastructure Services

```bash
docker compose up -d           # PostgreSQL + Redis
docker compose --profile airflow up -d  # + Airflow
docker compose --profile mail up -d     # + Mailhog
```

## Deployment Checklist

1. All tests passing on CI
2. Database migrations reviewed and tested
3. Environment variables configured in target environment
4. S3 buckets and IAM roles provisioned
5. Sentry DSN configured for error tracking
6. CORS origins updated for production domains
7. `MOCK_AUTH=false` in production
