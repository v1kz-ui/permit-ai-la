---
sidebar_position: 2
title: Environment Variables
---

# Environment Variables

All configuration is managed through environment variables. Copy `.env.example` to `.env` and customize as needed.

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://permitai:permitai@localhost:5432/permitai` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | `postgresql://permitai:permitai@localhost:5432/permitai` | Sync connection for Alembic migrations |

## Cache & Messaging

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for caching, rate limiting, pub/sub |

## AI & ML

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(empty)* | Claude API key. Required for PathfinderAI, Chat, and edge-case reasoning |

## External Data Sources

| Variable | Default | Description |
|----------|---------|-------------|
| `SOCRATA_APP_TOKEN` | *(empty)* | LA Open Data (Socrata) API token |
| `SOCRATA_DATASET_ID` | `hbkd-qubn` | LADBS permits dataset identifier |

## Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_AUTH` | `false` | When `true`, bypasses OAuth and auto-authenticates as a test user. **Use only in development.** |
| `ANGELENO_OAUTH_CLIENT_ID` | *(empty)* | Angeleno OAuth2 client ID |
| `ANGELENO_OAUTH_CLIENT_SECRET` | *(empty)* | Angeleno OAuth2 client secret |
| `ANGELENO_OAUTH_JWKS_URL` | *(empty)* | JSON Web Key Set endpoint for token validation |
| `ANGELENO_OAUTH_ISSUER` | *(empty)* | OAuth issuer URL |

## AWS / Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-west-2` | AWS region |
| `S3_BUCKET_DOCUMENTS` | `permitai-documents-dev` | S3 bucket for uploaded documents |
| `S3_BUCKET_DEAD_LETTERS` | *(empty)* | S3 bucket for failed message queue items |

## Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `FIREBASE_PROJECT_ID` | *(empty)* | Firebase project for push notifications |
| `FIREBASE_CREDENTIALS_PATH` | *(empty)* | Path to Firebase service account JSON |
| `TWILIO_ACCOUNT_SID` | *(empty)* | Twilio account SID for SMS |
| `TWILIO_AUTH_TOKEN` | *(empty)* | Twilio auth token |
| `TWILIO_FROM_NUMBER` | *(empty)* | Twilio sender phone number |

## Monitoring & Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | *(empty)* | Sentry error tracking DSN |
| `ENVIRONMENT` | `development` | Environment name (`development`, `staging`, `production`) |
| `LOG_LEVEL` | `DEBUG` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8081` | Comma-separated allowed origins |

## Frontend (Dashboard)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | *(empty)* | Mapbox GL token for map visualizations |
