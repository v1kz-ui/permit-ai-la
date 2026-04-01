"""Automatic audit logging middleware.

Intercepts mutating requests (POST, PATCH, PUT, DELETE) and logs to the
audit_log table.  GET requests and health-check endpoints are skipped.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import async_session_factory
from app.models.audit_log import AuditLog

logger = structlog.get_logger()

# Tables we explicitly track for before/after state
TRACKED_TABLES = {"projects", "clearances", "inspections"}

# Paths to skip entirely
SKIP_PATHS = {"/api/v1/health", "/health", "/docs", "/openapi.json", "/redoc"}

# Methods that trigger audit logging
MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method.upper()
        path = request.url.path

        # Skip non-mutating requests and health checks
        if method not in MUTATING_METHODS or any(path.startswith(s) for s in SKIP_PATHS):
            return await call_next(request)

        # Determine table from URL path
        table_name = self._extract_table(path)

        # Try to capture request body for POST/PATCH/PUT
        body_data: dict | None = None
        if method in ("POST", "PATCH", "PUT"):
            try:
                raw = await request.body()
                body_data = json.loads(raw) if raw else None
            except Exception:
                body_data = None

        # Execute the actual request
        response = await call_next(request)

        # Only log for successful mutations
        if response.status_code < 400 and table_name:
            user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None

            # Determine record_id from URL
            record_id = self._extract_record_id(path)

            action = {
                "POST": "INSERT",
                "PATCH": "UPDATE",
                "PUT": "UPDATE",
                "DELETE": "DELETE",
            }.get(method, "UNKNOWN")

            try:
                async with async_session_factory() as session:
                    entry = AuditLog(
                        table_name=table_name,
                        record_id=record_id or "unknown",
                        action=action,
                        old_value=None,
                        new_value=body_data if action in ("INSERT", "UPDATE") else None,
                        changed_by=user_id if isinstance(user_id, uuid.UUID) else None,
                    )
                    session.add(entry)
                    await session.commit()
            except Exception as exc:
                # Audit logging must never break the main request
                logger.error("audit_middleware_error", error=str(exc), path=path)

        return response

    @staticmethod
    def _extract_table(path: str) -> str | None:
        """Extract a table name from the URL path."""
        parts = [p for p in path.strip("/").split("/") if p]
        # Pattern: /api/v1/{resource}/...
        for tracked in TRACKED_TABLES:
            if tracked in parts:
                return tracked
        # Fallback: use the resource segment after 'v1'
        try:
            v1_idx = parts.index("v1")
            if v1_idx + 1 < len(parts):
                return parts[v1_idx + 1]
        except ValueError:
            pass
        return None

    @staticmethod
    def _extract_record_id(path: str) -> str | None:
        """Try to extract a UUID record id from the URL path."""
        parts = path.strip("/").split("/")
        for part in parts:
            try:
                uuid.UUID(part)
                return part
            except ValueError:
                continue
        return None
