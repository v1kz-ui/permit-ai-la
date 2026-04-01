"""Tests for monitoring and cache modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_monitoring():
    """Reset monitoring state between tests."""
    from app.core import monitoring

    monitoring._request_count.clear()
    monitoring._request_latency.clear()
    monitoring._error_count.clear()
    monitoring._active_connections = 0
    yield


class TestRecordRequest:
    def test_record_request_increments_counter(self):
        from app.core.monitoring import get_metrics, record_request

        record_request("GET", "/api/v1/health", 200, 15.0)
        record_request("GET", "/api/v1/health", 200, 20.0)
        record_request("POST", "/api/v1/projects", 201, 50.0)

        metrics = get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["requests"]["GET|/api/v1/health|200"]["count"] == 2
        assert metrics["requests"]["POST|/api/v1/projects|201"]["count"] == 1

    def test_record_request_tracks_latency(self):
        from app.core.monitoring import get_metrics, record_request

        record_request("GET", "/test", 200, 10.0)
        record_request("GET", "/test", 200, 20.0)
        record_request("GET", "/test", 200, 30.0)

        metrics = get_metrics()
        assert metrics["requests"]["GET|/test|200"]["p50_ms"] > 0


class TestRecordError:
    def test_record_error_increments(self):
        from app.core.monitoring import get_metrics, record_error

        record_error("ValueError", "/api/v1/projects")
        record_error("ValueError", "/api/v1/projects")
        record_error("TimeoutError", "/api/v1/health")

        metrics = get_metrics()
        assert metrics["total_errors"] == 3
        assert metrics["errors"]["ValueError|/api/v1/projects"]["count"] == 2
        assert metrics["errors"]["TimeoutError|/api/v1/health"]["count"] == 1


class TestHealthDetails:
    @pytest.mark.asyncio
    async def test_health_details_returns_expected_keys(self):
        with patch("app.core.redis.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.info = AsyncMock(
                return_value={"used_memory": 1024 * 1024 * 50, "connected_clients": 3}
            )
            mock_redis.return_value = mock_redis_instance

            with patch("psutil.Process") as mock_process:
                mock_mem = MagicMock()
                mock_mem.rss = 100 * 1024 * 1024
                mock_mem.vms = 200 * 1024 * 1024
                mock_process.return_value.memory_info.return_value = mock_mem

                from app.core.monitoring import get_health_details

                details = await get_health_details()

                assert "uptime_seconds" in details
                assert "memory" in details
                assert "rss_mb" in details["memory"]
                assert "database_pool" in details
                assert "redis" in details
                assert details["redis"]["status"] == "connected"


class TestMetricsFormat:
    def test_metrics_format_prometheus(self):
        from app.core.monitoring import get_metrics_prometheus, record_request

        record_request("GET", "/health", 200, 5.0)

        output = get_metrics_prometheus()
        assert "permitai_requests_total" in output
        assert "permitai_active_connections" in output
        assert "permitai_uptime_seconds" in output
        assert 'method="GET"' in output


class TestCacheService:
    @pytest.mark.asyncio
    async def test_cache_get_set_delete(self):
        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            store = {}
            mock_redis_instance = AsyncMock()

            async def mock_get(key):
                return store.get(key)

            async def mock_set(key, value, ex=None):
                store[key] = value

            async def mock_delete(key):
                store.pop(key, None)

            mock_redis_instance.get = mock_get
            mock_redis_instance.set = mock_set
            mock_redis_instance.delete = mock_delete
            mock_redis.return_value = mock_redis_instance

            from app.core.cache import CacheService

            cache = CacheService()

            # Test set and get
            await cache.set("test_key", {"name": "PermitAI"}, ttl=60)
            result = await cache.get("test_key")
            assert result == {"name": "PermitAI"}

            # Test delete
            await cache.delete("test_key")
            result = await cache.get("test_key")
            assert result is None

            # Test stats
            stats = cache.get_stats()
            assert stats["sets"] == 1
            assert stats["hits"] == 1
            assert stats["misses"] == 1
            assert stats["deletes"] == 1

    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        call_count = 0

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            store = {}
            mock_redis_instance = AsyncMock()

            async def mock_get(key):
                return store.get(key)

            async def mock_set(key, value, ex=None):
                store[key] = value

            mock_redis_instance.get = mock_get
            mock_redis_instance.set = mock_set
            mock_redis.return_value = mock_redis_instance

            from app.core.cache import cache_decorator

            @cache_decorator(ttl=60, key_prefix="test")
            async def expensive_function(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x * 2

            # First call should execute the function
            result1 = await expensive_function(5)
            assert result1 == 10
            assert call_count == 1

            # Second call should return cached result
            result2 = await expensive_function(5)
            assert result2 == 10
            assert call_count == 1  # Not called again
