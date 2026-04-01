from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import engine
from app.core.redis import close_redis, get_redis
from app.core.monitoring import decrement_connections, increment_connections, record_request
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.error_handler import error_handler_middleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.security import SecurityHeadersMiddleware

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.ENVIRONMENT == "development"
        else structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log = structlog.get_logger()
    await log.ainfo("Starting PermitAI LA API", environment=settings.ENVIRONMENT)

    # Verify database connectivity
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )
    await log.ainfo("Database connection verified")

    # Verify Redis connectivity
    redis = await get_redis()
    await redis.ping()
    await log.ainfo("Redis connection verified")

    # Warm cache with frequently accessed data
    from app.core.cache import warm_cache
    await warm_cache()
    await log.ainfo("Cache warming complete")

    # Initialize Sentry if configured
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    yield

    # Shutdown
    await close_redis()
    await engine.dispose()
    await log.ainfo("PermitAI LA API shut down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PermitAI LA",
        description="AI-powered platform to accelerate fire rebuilding permit processes in LA",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware (order matters: outermost first)
    app.middleware("http")(error_handler_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Monitoring middleware for request counting
    @app.middleware("http")
    async def monitoring_middleware(request, call_next):
        import time as _time

        increment_connections()
        start = _time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (_time.perf_counter() - start) * 1000
            record_request(
                request.method, request.url.path, response.status_code, duration_ms
            )
            return response
        finally:
            decrement_connections()

    # Routes
    from app.api.v1.router import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
