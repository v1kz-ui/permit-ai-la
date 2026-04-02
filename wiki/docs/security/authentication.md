---
sidebar_position: 1
title: Authentication & Authorization
---

# Authentication & Authorization

## Angeleno OAuth

PermitAI uses LA's Angeleno identity platform for authentication. Users sign in with their Angeleno account, and the backend validates the OAuth bearer token against the JWKS endpoint.

**Configuration:**
```
ANGELENO_OAUTH_CLIENT_ID=<client_id>
ANGELENO_OAUTH_CLIENT_SECRET=<client_secret>
ANGELENO_OAUTH_JWKS_URL=<jwks_endpoint>
ANGELENO_OAUTH_ISSUER=<issuer_url>
```

**Development mode:** Set `MOCK_AUTH=true` to bypass OAuth and auto-authenticate as a mock user. This should never be used in production.

## Role-Based Access Control (RBAC)

| Role | Description | Access Level |
|------|-------------|-------------|
| `homeowner` | Property owner rebuilding after fire | Own projects only |
| `contractor` | Licensed contractor | Own projects only |
| `architect` | Licensed architect | Own projects only |
| `staff` | City staff member | All projects, analytics, reports |
| `admin` | System administrator | Everything + user management, audit, cache |

### Permission Matrix

| Endpoint Group | Homeowner | Staff | Admin |
|---------------|-----------|-------|-------|
| Own projects | Yes | Yes | Yes |
| All projects | No | Yes | Yes |
| Analytics | No | Yes | Yes |
| Reports | No | Yes | Yes |
| User management | No | No | Yes |
| Audit log | No | No | Yes |
| Cache control | No | No | Yes |
| Chat | Yes (20/hr) | Yes | Yes |

## Security Headers

The `SecurityHeadersMiddleware` adds:
- `Strict-Transport-Security` (HSTS)
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy`
- `Referrer-Policy: strict-origin-when-cross-origin`

## CORS

Configured via `CORS_ORIGINS` environment variable. Default allows `localhost:3000` (dashboard) and `localhost:8081` (mobile).

## Rate Limiting

Redis-backed rate limiting with fail-open behavior:
- **Chat:** 20 messages per hour per user
- **General API:** Configurable thresholds
- If Redis is unavailable, rate limiting is skipped (fail-open)
