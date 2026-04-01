import uuid
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None
_jwks_cache_time: datetime | None = None
JWKS_CACHE_TTL_SECONDS = 3600


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_cache_time
    now = datetime.now(timezone.utc)

    if (
        _jwks_cache is not None
        and _jwks_cache_time is not None
        and (now - _jwks_cache_time).total_seconds() < JWKS_CACHE_TTL_SECONDS
    ):
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(settings.ANGELENO_OAUTH_JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache


class MockUser:
    def __init__(self):
        self.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.email = "dev@permitai.la"
        self.name = "Dev User"
        self.role = "admin"
        self.angeleno_id = "mock-angeleno-001"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if settings.MOCK_AUTH and settings.ENVIRONMENT == "production":
        raise RuntimeError("MOCK_AUTH cannot be enabled in production")

    if settings.MOCK_AUTH:
        return MockUser()

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = credentials.credentials

    try:
        jwks = await _fetch_jwks()
        unverified_header = jwt.get_unverified_header(token)

        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token signing key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.ANGELENO_OAUTH_CLIENT_ID,
            issuer=settings.ANGELENO_OAUTH_ISSUER,
        )

        class AuthenticatedUser:
            def __init__(self, claims: dict):
                try:
                    self.id = uuid.UUID(claims.get("sub", ""))
                except (ValueError, AttributeError):
                    raise HTTPException(status_code=401, detail="Invalid token subject")
                self.email = claims.get("email", "")
                self.name = claims.get("name", "")
                self.role = claims.get("role", "homeowner")
                self.angeleno_id = claims.get("angeleno_id", "")

        return AuthenticatedUser(payload)

    except JWTError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise HTTPException(status_code=403, detail="Invalid or expired token")
