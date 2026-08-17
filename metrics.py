"""
In-process metrics + telemetry.

The interesting cost in this service isn't request count, it's
*optimization time as a function of stop count* -- nearest-neighbor +
2-opt is polynomial but still O(n^2) per 2-opt pass, so latency grows
with n in a way that matters for capacity planning. This module tracks
that relationship directly (latency bucketed by stop count) alongside
the usual request/error counters, and exposes everything in Prometheus
text format for scraping by Prometheus/Grafana.

Deliberately dependency-free (no prometheus_client package) so the
project keeps its "pip install -r requirements.txt and go" simplicity.
In a real multi-instance deployment these in-memory counters would need
to move to shared storage (StatsD/Prometheus pushgateway) -- noted in
the README, same tradeoff as the URL shortener's cache/rate-limiter.
"""

import threading
import time
from collections import defaultdict
from typing import Dict, List

_lock = threading.Lock()

_request_count: Dict[str, int] = defaultdict(int)   # "METHOD path status" -> count
_error_count: Dict[str, int] = defaultdict(int)      # endpoint -> count

_MAX_SAMPLES = 500
_latencies: Dict[str, List[float]] = defaultdict(list)          # endpoint -> [ms, ...]
_optimize_latency_by_stops: Dict[str, List[float]] = defaultdict(list)  # bucket -> [ms, ...]


def _stop_count_bucket(n: int) -> str:
    if n <= 10:
        return "1-10"
    if n <= 50:
        return "11-50"
    if n <= 150:
        return "51-150"
    return "150+"


def record_request(endpoint: str, method: str, status: int, duration_ms: float) -> None:
    with _lock:
        key = f"{method} {endpoint} {status}"
        _request_count[key] += 1
        if status >= 500:
            _error_count[endpoint] += 1

        samples = _latencies[endpoint]
        samples.append(duration_ms)
        if len(samples) > _MAX_SAMPLES:
            samples.pop(0)


def record_optimize(stop_count: int, duration_ms: float) -> None:
    with _lock:
        bucket = _stop_count_bucket(stop_count)
        samples = _optimize_latency_by_stops[bucket]
        samples.append(duration_ms)
        if len(samples) > _MAX_SAMPLES:
            samples.pop(0)


def _percentile(sorted_samples: List[float], pct: float) -> float:
    if not sorted_samples:
        return 0.0
    idx = min(len(sorted_samples) - 1, int(round(pct / 100 * (len(sorted_samples) - 1))))
    return sorted_samples[idx]


def snapshot() -> dict:
    with _lock:
        latency_stats = {}
        for endpoint, samples in _latencies.items():
            s = sorted(samples)
            latency_stats[endpoint] = {
                "count": len(s),
                "p50_ms": round(_percentile(s, 50), 2),
                "p95_ms": round(_percentile(s, 95), 2),
                "max_ms": round(s[-1], 2) if s else 0.0,
            }

        optimize_stats = {}
        for bucket, samples in _optimize_latency_by_stops.items():
            s = sorted(samples)
            optimize_stats[bucket] = {
                "count": len(s),
                "p50_ms": round(_percentile(s, 50), 2),
                "p95_ms": round(_percentile(s, 95), 2),
            }

        return {
            "requests": dict(_request_count),
            "errors": dict(_error_count),
            "latency": latency_stats,
            "optimize_latency_by_stop_count": optimize_stats,
        }


def prometheus_text() -> str:
    data = snapshot()
    lines = []

    lines.append("# HELP optimizer_requests_total Total requests by method, endpoint, and status")
    lines.append("# TYPE optimizer_requests_total counter")
    for key, count in data["requests"].items():
        method, endpoint, status = key.split(" ", 2)
        lines.append(
            f'optimizer_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
        )

    lines.append("# HELP optimizer_optimize_latency_ms_p95 95th percentile optimize() time by stop-count bucket")
    lines.append("# TYPE optimizer_optimize_latency_ms_p95 gauge")
    for bucket, stats in data["optimize_latency_by_stop_count"].items():
        lines.append(f'optimizer_optimize_latency_ms_p95{{stops="{bucket}"}} {stats["p95_ms"]}')

    return "\n".join(lines) + "\n"


def reset() -> None:
    with _lock:
        _request_count.clear()
        _error_count.clear()
        _latencies.clear()
        _optimize_latency_by_stops.clear()


def timer() -> float:
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
