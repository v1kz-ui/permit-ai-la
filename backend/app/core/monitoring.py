"""Application monitoring and metrics collection."""

import os
import time
from collections import defaultdict
from threading import Lock
from typing import Any

import structlog

logger = structlog.get_logger()

_start_time = time.time()
_lock = Lock()

# Metrics stores
_request_count: dict[str, int] = defaultdict(int)
_request_latency: dict[str, list[float]] = defaultdict(list)
_error_count: dict[str, int] = defaultdict(int)
_active_connections: int = 0


def record_request(method: str, path: str, status_code: int, duration: float) -> None:
    """Record a completed request with its metrics."""
    key = f"{method}|{path}|{status_code}"
    with _lock:
        _request_count[key] += 1
        _request_latency[key].append(duration)
        # Keep only last 1000 latency samples per key to bound memory
        if len(_request_latency[key]) > 1000:
            _request_latency[key] = _request_latency[key][-1000:]


def record_error(error_type: str, path: str) -> None:
    """Record an error occurrence."""
    key = f"{error_type}|{path}"
    with _lock:
        _error_count[key] += 1


def increment_connections() -> None:
    """Increment active connection count."""
    global _active_connections
    with _lock:
        _active_connections += 1


def decrement_connections() -> None:
    """Decrement active connection count."""
    global _active_connections
    with _lock:
        _active_connections = max(0, _active_connections - 1)


def _percentile(values: list[float], p: float) -> float:
    """Calculate the p-th percentile of a list of values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def get_metrics() -> dict[str, Any]:
    """Return all collected metrics as a dictionary."""
    with _lock:
        total_requests = sum(_request_count.values())
        total_errors = sum(_error_count.values())

        # Flatten all latencies for global percentiles
        all_latencies = []
        for latencies in _request_latency.values():
            all_latencies.extend(latencies)

        request_breakdown = {}
        for key, count in _request_count.items():
            method, path, status = key.split("|")
            request_breakdown[key] = {
                "method": method,
                "path": path,
                "status_code": int(status),
                "count": count,
                "p50_ms": round(_percentile(_request_latency.get(key, []), 50), 2),
                "p95_ms": round(_percentile(_request_latency.get(key, []), 95), 2),
                "p99_ms": round(_percentile(_request_latency.get(key, []), 99), 2),
            }

        error_breakdown = {}
        for key, count in _error_count.items():
            error_type, path = key.split("|")
            error_breakdown[key] = {
                "error_type": error_type,
                "path": path,
                "count": count,
            }

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "active_connections": _active_connections,
            "uptime_seconds": round(time.time() - _start_time, 1),
            "global_p50_ms": round(_percentile(all_latencies, 50), 2),
            "global_p95_ms": round(_percentile(all_latencies, 95), 2),
            "global_p99_ms": round(_percentile(all_latencies, 99), 2),
            "requests": request_breakdown,
            "errors": error_breakdown,
        }


def get_metrics_prometheus() -> str:
    """Return metrics in Prometheus text exposition format."""
    lines: list[str] = []
    metrics = get_metrics()

    lines.append("# HELP permitai_requests_total Total number of HTTP requests.")
    lines.append("# TYPE permitai_requests_total counter")
    for info in metrics["requests"].values():
        lines.append(
            f'permitai_requests_total{{method="{info["method"]}",path="{info["path"]}",'
            f'status="{info["status_code"]}"}} {info["count"]}'
        )

    lines.append("# HELP permitai_errors_total Total number of errors.")
    lines.append("# TYPE permitai_errors_total counter")
    for info in metrics["errors"].values():
        lines.append(
            f'permitai_errors_total{{type="{info["error_type"]}",path="{info["path"]}"}} {info["count"]}'
        )

    lines.append("# HELP permitai_active_connections Current active connections.")
    lines.append("# TYPE permitai_active_connections gauge")
    lines.append(f'permitai_active_connections {metrics["active_connections"]}')

    lines.append("# HELP permitai_uptime_seconds Application uptime in seconds.")
    lines.append("# TYPE permitai_uptime_seconds gauge")
    lines.append(f'permitai_uptime_seconds {metrics["uptime_seconds"]}')

    lines.append("# HELP permitai_latency_p99_ms P99 latency in milliseconds.")
    lines.append("# TYPE permitai_latency_p99_ms gauge")
    lines.append(f'permitai_latency_p99_ms {metrics["global_p99_ms"]}')

    return "\n".join(lines) + "\n"


async def get_health_details() -> dict[str, Any]:
    """Extended health check with DB pool stats, Redis info, uptime, and memory."""
    import psutil

    from app.core.database import engine
    from app.core.redis import get_redis

    details: dict[str, Any] = {
        "uptime_seconds": round(time.time() - _start_time, 1),
        "active_connections": _active_connections,
    }

    # Memory usage
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    details["memory"] = {
        "rss_mb": round(mem_info.rss / 1024 / 1024, 1),
        "vms_mb": round(mem_info.vms / 1024 / 1024, 1),
    }

    # Database pool stats
    pool = engine.pool
    details["database_pool"] = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }

    # Redis info
    try:
        redis = await get_redis()
        redis_info = await redis.info(section="memory")
        details["redis"] = {
            "status": "connected",
            "used_memory_mb": round(redis_info.get("used_memory", 0) / 1024 / 1024, 1),
            "connected_clients": redis_info.get("connected_clients", "N/A"),
        }
    except Exception as exc:
        details["redis"] = {"status": f"error: {exc}"}

    return details
