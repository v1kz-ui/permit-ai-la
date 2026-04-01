"""Shared test fixtures for PermitAI LA backend tests."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.database import get_db_session
from app.core.redis import get_redis
from app.main import app
from app.middleware.auth import get_current_user
from app.models.base import Base


# Mock user for testing
class MockTestUser:
    def __init__(self, role="admin"):
        self.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.email = "test@permitai.la"
        self.name = "Test User"
        self.role = role
        self.angeleno_id = "test-angeleno-001"


@pytest.fixture
def mock_user():
    return MockTestUser()


@pytest.fixture
def mock_homeowner():
    return MockTestUser(role="homeowner")


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    redis.ping = AsyncMock()
    redis.pipeline = MagicMock()
    redis.exists = AsyncMock(return_value=False)
    redis.info = AsyncMock(return_value={"used_memory": 1024, "connected_clients": 1})
    return redis


@pytest.fixture
def mock_db():
    """Mock async database session for tests that don't need a real DB."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
            scalar_one_or_none=MagicMock(return_value=None),
            scalar=MagicMock(return_value=0),
        )
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _mock_engine(mock_redis_instance):
    """Build a mock SQLAlchemy engine that won't try to connect."""
    mock_eng = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    @asynccontextmanager
    async def _begin():
        yield mock_conn

    mock_eng.begin = _begin
    mock_eng.dispose = AsyncMock()
    mock_eng.pool = MagicMock(
        size=MagicMock(return_value=5),
        checkedin=MagicMock(return_value=4),
        checkedout=MagicMock(return_value=1),
        overflow=MagicMock(return_value=0),
    )
    return mock_eng


@pytest.fixture
def client(mock_user, mock_redis, mock_db):
    """FastAPI test client with mocked dependencies and lifespan patched."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db

    mock_eng = _mock_engine(mock_redis)
    with patch("app.main.engine", mock_eng), \
         patch("app.main.get_redis", AsyncMock(return_value=mock_redis)), \
         patch("app.main.close_redis", AsyncMock()), \
         patch("app.core.cache.warm_cache", AsyncMock()):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def homeowner_client(mock_homeowner, mock_redis, mock_db):
    """FastAPI test client as homeowner role."""
    app.dependency_overrides[get_current_user] = lambda: mock_homeowner
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db

    mock_eng = _mock_engine(mock_redis)
    with patch("app.main.engine", mock_eng), \
         patch("app.main.get_redis", AsyncMock(return_value=mock_redis)), \
         patch("app.main.close_redis", AsyncMock()), \
         patch("app.core.cache.warm_cache", AsyncMock()):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()
