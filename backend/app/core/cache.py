"""Centralized caching layer with Redis backend."""

import functools
import hashlib
import json
import time
from collections import defaultdict
from typing import Any, Callable

import structlog

from app.core.redis import get_redis

logger = structlog.get_logger()


class CacheService:
    """Redis-backed cache service with stats tracking."""

    def __init__(self):
        self._stats: dict[str, int] = defaultdict(int)

    async def get(self, key: str) -> Any | None:
        """Get a value from cache. Returns None on miss."""
        redis = await get_redis()
        raw = await redis.get(f"cache:{key}")
        if raw is None:
            self._stats["misses"] += 1
            return None
        self._stats["hits"] += 1
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set a value in cache with TTL (seconds)."""
        redis = await get_redis()
        serialized = json.dumps(value, default=str)
        await redis.set(f"cache:{key}", serialized, ex=ttl)
        self._stats["sets"] += 1

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        redis = await get_redis()
        await redis.delete(f"cache:{key}")
        self._stats["deletes"] += 1

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern. Returns count of deleted keys."""
        redis = await get_redis()
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=f"cache:{pattern}", count=100)
            if keys:
                await redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        self._stats["pattern_invalidations"] += 1
        return deleted

    def get_stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics."""
        hits = self._stats.get("hits", 0)
        misses = self._stats.get("misses", 0)
        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 4) if total > 0 else 0.0,
            "miss_rate": round(misses / total, 4) if total > 0 else 0.0,
            "sets": self._stats.get("sets", 0),
            "deletes": self._stats.get("deletes", 0),
            "pattern_invalidations": self._stats.get("pattern_invalidations", 0),
        }


# Global cache service instance
cache_service = CacheService()


def cache_decorator(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching async function results.

    Args:
        ttl: Time-to-live in seconds (default 5 minutes).
        key_prefix: Prefix for the cache key.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build a deterministic cache key from function name + arguments
            parts = [key_prefix or func.__module__ + "." + func.__qualname__]
            for arg in args:
                parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                parts.append(f"{k}={v}")
            raw_key = ":".join(parts)
            cache_key = hashlib.md5(raw_key.encode()).hexdigest()

            # Try cache first
            cached = await cache_service.get(cache_key)
            if cached is not None:
                return cached

            # Call the function and cache the result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator


async def warm_cache() -> None:
    """Pre-populate cache with frequently accessed data."""
    try:
        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            import sqlalchemy

            # Warm clearance types
            result = await session.execute(
                sqlalchemy.text("SELECT id, name, description FROM clearance_types LIMIT 100")
            )
            rows = result.fetchall()
            if rows:
                clearance_types = [
                    {"id": str(r[0]), "name": r[1], "description": r[2]} for r in rows
                ]
                await cache_service.set("clearance_types:all", clearance_types, ttl=3600)
                await logger.ainfo("Cache warmed: clearance_types", count=len(clearance_types))

            # Warm parcel count
            result = await session.execute(sqlalchemy.text("SELECT COUNT(*) FROM parcels"))
            count = result.scalar()
            await cache_service.set("parcels:count", count, ttl=1800)
            await logger.ainfo("Cache warmed: parcels count", count=count)

    except Exception as exc:
        await logger.awarning("Cache warming failed (non-fatal)", error=str(exc))
