"""Load testing script using httpx for concurrent HTTP requests.

Usage:
    python -m app.scripts.load_test --url http://localhost:8000 --users 100 --duration 60
"""

import argparse
import asyncio
import random
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field

import httpx


@dataclass
class LoadTestResults:
    """Aggregated load test results."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: list[float] = field(default_factory=list)
    errors_by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    status_codes: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    start_time: float = 0.0
    end_time: float = 0.0


# Endpoints to test
ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/health", "weight": 3},
    {"method": "GET", "path": "/api/v1/projects", "weight": 2},
    {"method": "GET", "path": "/api/v1/clearances", "weight": 2},
    {
        "method": "POST",
        "path": "/api/v1/pathfinder/quick-analysis",
        "weight": 1,
        "json": {
            "address": "123 Main St, Los Angeles, CA 90001",
            "project_type": "single_family_rebuild",
        },
    },
]


def _select_endpoint() -> dict:
    """Select a random endpoint weighted by frequency."""
    weighted = []
    for ep in ENDPOINTS:
        weighted.extend([ep] * ep["weight"])
    return random.choice(weighted)


async def _simulate_user(
    client: httpx.AsyncClient,
    base_url: str,
    duration: float,
    results: LoadTestResults,
) -> None:
    """Simulate a single user making requests for the given duration."""
    end_time = time.monotonic() + duration

    while time.monotonic() < end_time:
        endpoint = _select_endpoint()
        url = f"{base_url}{endpoint['path']}"
        method = endpoint["method"]

        start = time.monotonic()
        try:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=endpoint.get("json", {}))

            latency_ms = (time.monotonic() - start) * 1000
            results.latencies.append(latency_ms)
            results.status_codes[response.status_code] += 1
            results.total_requests += 1

            if response.status_code < 400:
                results.successful_requests += 1
            else:
                results.failed_requests += 1

        except httpx.TimeoutException:
            results.total_requests += 1
            results.failed_requests += 1
            results.errors_by_type["timeout"] += 1
        except httpx.ConnectError:
            results.total_requests += 1
            results.failed_requests += 1
            results.errors_by_type["connection_error"] += 1
        except Exception as exc:
            results.total_requests += 1
            results.failed_requests += 1
            results.errors_by_type[type(exc).__name__] += 1

        # Small random delay between requests (50-200ms)
        await asyncio.sleep(random.uniform(0.05, 0.2))


def _percentile(values: list[float], p: float) -> float:
    """Calculate percentile from a sorted list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def _print_results(results: LoadTestResults, num_users: int, duration: int) -> None:
    """Print formatted load test results."""
    elapsed = results.end_time - results.start_time
    rps = results.total_requests / elapsed if elapsed > 0 else 0

    print("\n" + "=" * 70)
    print("  LOAD TEST RESULTS")
    print("=" * 70)
    print(f"  Concurrent Users:    {num_users}")
    print(f"  Duration:            {duration}s (actual: {elapsed:.1f}s)")
    print(f"  Total Requests:      {results.total_requests}")
    print(f"  Requests/sec:        {rps:.1f}")
    print("-" * 70)
    print(f"  Successful:          {results.successful_requests}")
    print(f"  Failed:              {results.failed_requests}")
    success_rate = (
        results.successful_requests / results.total_requests * 100
        if results.total_requests > 0
        else 0
    )
    print(f"  Success Rate:        {success_rate:.1f}%")
    print("-" * 70)

    if results.latencies:
        print("  Latency (ms):")
        print(f"    Min:               {min(results.latencies):.1f}")
        print(f"    Mean:              {statistics.mean(results.latencies):.1f}")
        print(f"    P50:               {_percentile(results.latencies, 50):.1f}")
        print(f"    P95:               {_percentile(results.latencies, 95):.1f}")
        print(f"    P99:               {_percentile(results.latencies, 99):.1f}")
        print(f"    Max:               {max(results.latencies):.1f}")
    print("-" * 70)

    if results.status_codes:
        print("  Status Codes:")
        for code, count in sorted(results.status_codes.items()):
            print(f"    {code}:               {count}")

    if results.errors_by_type:
        print("  Errors by Type:")
        for error_type, count in sorted(results.errors_by_type.items()):
            print(f"    {error_type}:  {count}")

    print("=" * 70 + "\n")


async def run_load_test(base_url: str, num_users: int, duration_seconds: int) -> LoadTestResults:
    """Run a load test with the specified number of concurrent users.

    Args:
        base_url: The base URL of the API (e.g. http://localhost:8000).
        num_users: Number of concurrent simulated users.
        duration_seconds: How long to run the test in seconds.

    Returns:
        LoadTestResults with aggregated metrics.
    """
    results = LoadTestResults()

    print(f"Starting load test: {num_users} users, {duration_seconds}s against {base_url}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        results.start_time = time.monotonic()

        tasks = [
            _simulate_user(client, base_url, duration_seconds, results)
            for _ in range(num_users)
        ]
        await asyncio.gather(*tasks)

        results.end_time = time.monotonic()

    _print_results(results, num_users, duration_seconds)
    return results


def main():
    parser = argparse.ArgumentParser(description="PermitAI LA Load Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")

    args = parser.parse_args()
    asyncio.run(run_load_test(args.url, args.users, args.duration))


if __name__ == "__main__":
    main()
