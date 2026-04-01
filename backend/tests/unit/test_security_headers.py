"""Tests for security headers middleware."""

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.middleware.security import SecurityHeadersMiddleware


@pytest.fixture
def app_with_security():
    """Create a minimal FastAPI app with security middleware."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return app


@pytest.fixture
async def client(app_with_security):
    transport = ASGITransport(app=app_with_security)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
class TestSecurityHeaders:
    async def test_csp_header_present(self, client):
        response = await client.get("/test")
        assert response.status_code == 200
        csp = response.headers.get("content-security-policy")
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    async def test_hsts_header_present(self, client):
        response = await client.get("/test")
        hsts = response.headers.get("strict-transport-security")
        assert hsts is not None
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    async def test_xframe_deny(self, client):
        response = await client.get("/test")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_nosniff_header(self, client):
        response = await client.get("/test")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_referrer_policy(self, client):
        response = await client.get("/test")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_permissions_policy(self, client):
        response = await client.get("/test")
        pp = response.headers.get("permissions-policy")
        assert pp is not None
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp
