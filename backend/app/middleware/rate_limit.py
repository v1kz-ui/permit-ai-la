import time

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.redis import get_redis

logger = structlog.get_logger()

RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW_SECONDS = 60


async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for health checks
    if request.url.path in ("/api/v1/health", "/health", "/docs", "/openapi.json"):
        return await call_next(request)

    user = getattr(request.state, "user", None)
    if user is None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:ip:{client_ip}"
    else:
        key = f"ratelimit:user:{user.id}"

    try:
        redis = await get_redis()
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        pipe = redis.pipeline()
        await pipe.zremrangebyscore(key, 0, window_start)
        await pipe.zadd(key, {str(now): now})
        await pipe.zcard(key)
        await pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)
        results = await pipe.execute()

        request_count = results[2]

        if request_count > RATE_LIMIT_REQUESTS:
            retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - window_start))
            return JSONResponse(
                status_code=429,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    "instance": request.url.path,
                },
                headers={"Retry-After": str(retry_after)},
            )
    except Exception as e:
        await logger.awarning("Rate limiting unavailable", error=str(e))

    return await call_next(request)
