"""Integration-test configuration.

Connects to the real PostgreSQL instance started by docker-compose.test.yml
(postgres:16-alpine on localhost:5433) and provides async session fixtures with
per-test rollback semantics.

Run integration tests with:
    pytest tests/integration/ -m integration
"""

import os
import uuid

# Override DATABASE_URL before any app module is imported so that
# pydantic-settings picks up the test database connection string.
TEST_DATABASE_URL_ASYNC = "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"
TEST_DATABASE_URL_SYNC  = "postgresql://testuser:testpass@localhost:5433/testdb"

os.environ["DATABASE_URL"]      = TEST_DATABASE_URL_ASYNC
os.environ["DATABASE_URL_SYNC"] = TEST_DATABASE_URL_SYNC
os.environ["MOCK_AUTH"]         = "True"
os.environ["REDIS_URL"]         = "redis://localhost:6380/0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# App imports must come AFTER os.environ overrides above
from app.core.database import get_db_session
from app.main import app
from app.middleware.auth import get_current_user
from app.models.base import Base
from app.models.clearance import Clearance  # noqa: F401  – register with metadata
from app.models.document import Document    # noqa: F401
from app.models.inspection import Inspection  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.project import Project      # noqa: F401
from app.models.user import User
from app.schemas.common import UserRole

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Async engine pointed at the test database
# ---------------------------------------------------------------------------
_async_engine = create_async_engine(
    TEST_DATABASE_URL_ASYNC,
    echo=False,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
)

_async_session_factory = async_sessionmaker(
    _async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Schema lifecycle (session-scoped – create once, drop once)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _create_tables():
    """Create all tables synchronously at the start of the session."""
    sync_engine = create_engine(TEST_DATABASE_URL_SYNC, echo=False)
    # Ensure enums and tables exist; use checkfirst so re-runs don't fail
    Base.metadata.create_all(sync_engine, checkfirst=True)
    yield
    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()


# ---------------------------------------------------------------------------
# Async session fixture with per-test rollback
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session(_create_tables) -> AsyncSession:
    """Yield an AsyncSession that is rolled back after every test."""
    async with _async_engine.connect() as conn:
        await conn.begin()
        # Wrap in a savepoint so each test is isolated
        await conn.begin_nested()

        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ---------------------------------------------------------------------------
# FastAPI TestClient with DB and auth overrides
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client(_create_tables):
    """TestClient that overrides get_db_session with a real DB session.

    Auth is left as MOCK_AUTH=True (admin role via MockUser).  Individual tests
    that need a specific role should override get_current_user themselves.
    """
    # We use a fresh session per request (standard pattern for integration tests)
    async def _override_get_db():
        async with _async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# Helper: create a user directly in the DB
# ---------------------------------------------------------------------------

async def _create_user(db_session: AsyncSession, *, role: str, suffix: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{suffix}-{uuid.uuid4().hex[:6]}@test.permitai.la",
        name=f"Test {suffix.title()}",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """A persisted homeowner User for use in integration tests."""
    return await _create_user(db_session, role=UserRole.HOMEOWNER, suffix="homeowner")


@pytest.fixture
async def test_staff(db_session: AsyncSession) -> User:
    """A persisted staff User for use in integration tests."""
    return await _create_user(db_session, role=UserRole.STAFF, suffix="staff")


# ---------------------------------------------------------------------------
# Convenience: build a MockUser-like object for auth override
# ---------------------------------------------------------------------------

class _FakeAuthUser:
    """Minimal user object accepted by FastAPI dependency injection."""

    def __init__(self, db_user: User):
        self.id          = db_user.id
        self.email       = db_user.email
        self.name        = db_user.name
        self.role        = db_user.role
        self.angeleno_id = ""


def make_auth_override(db_user: User):
    """Return a FastAPI dependency override that authenticates as *db_user*."""
    fake = _FakeAuthUser(db_user)

    def _override():
        return fake

    return _override
