import logging
import time
import os
from typing import Dict, Any, Optional

logger = logging.getLogger("successcore.metrics")

METRICS_REGISTRY: Dict[str, Any] = {
    "http_requests_total": 0,
    "http_requests_by_status": {},
    "http_request_latency_ms": [],
    "agent_runs_total": 0,
    "agent_runs_by_status": {},
    "agent_runs_by_type": {},
    "agent_token_usage_total": 0,
    "agent_cost_total_usd": 0.0,
    "db_connections_active": 0,
    "db_connections_idle": 0,
    "db_connections_overflow": 0,
    "db_query_count": 0,
    "redis_connects_total": 0,
    "redis_errors_total": 0,
    "cache_hits_total": 0,
    "cache_misses_total": 0,
    "login_attempts_total": 0,
    "login_failures_total": 0,
    "rate_limit_hits_total": 0,
}

_pending_latencies: list = []
_last_snapshot_time = time.monotonic()


def record_http_request(method: str, path: str, status_code: int, latency_ms: float):
    METRICS_REGISTRY["http_requests_total"] = METRICS_REGISTRY.get("http_requests_total", 0) + 1
    status_bucket = f"status_{status_code // 100}xx"
    status_map = METRICS_REGISTRY.setdefault("http_requests_by_status", {})
    status_map[status_bucket] = status_map.get(status_bucket, 0) + 1
    _pending_latencies.append(latency_ms)
    if len(_pending_latencies) > 1000:
        _pending_latencies.pop(0)


def record_agent_run(agent_type: str, status: str, tokens: int, cost: float):
    METRICS_REGISTRY["agent_runs_total"] = METRICS_REGISTRY.get("agent_runs_total", 0) + 1
    status_map = METRICS_REGISTRY.setdefault("agent_runs_by_status", {})
    status_map[status] = status_map.get(status, 0) + 1
    type_map = METRICS_REGISTRY.setdefault("agent_runs_by_type", {})
    type_map[agent_type] = type_map.get(agent_type, 0) + 1
    METRICS_REGISTRY["agent_token_usage_total"] = METRICS_REGISTRY.get("agent_token_usage_total", 0) + tokens
    METRICS_REGISTRY["agent_cost_total_usd"] = round(METRICS_REGISTRY.get("agent_cost_total_usd", 0) + cost, 6)


def record_db_connection_acquired():
    METRICS_REGISTRY["db_connections_active"] = METRICS_REGISTRY.get("db_connections_active", 0) + 1
    METRICS_REGISTRY["db_query_count"] = METRICS_REGISTRY.get("db_query_count", 0) + 1


def record_db_connection_released():
    METRICS_REGISTRY["db_connections_active"] = max(0, METRICS_REGISTRY.get("db_connections_active", 0) - 1)


def record_cache_hit():
    METRICS_REGISTRY["cache_hits_total"] = METRICS_REGISTRY.get("cache_hits_total", 0) + 1


def record_cache_miss():
    METRICS_REGISTRY["cache_misses_total"] = METRICS_REGISTRY.get("cache_misses_total", 0) + 1


def record_login_attempt(success: bool):
    METRICS_REGISTRY["login_attempts_total"] = METRICS_REGISTRY.get("login_attempts_total", 0) + 1
    if not success:
        METRICS_REGISTRY["login_failures_total"] = METRICS_REGISTRY.get("login_failures_total", 0) + 1


def record_rate_limit_hit():
    METRICS_REGISTRY["rate_limit_hits_total"] = METRICS_REGISTRY.get("rate_limit_hits_total", 0) + 1


def record_redis_connect():
    METRICS_REGISTRY["redis_connects_total"] = METRICS_REGISTRY.get("redis_connects_total", 0) + 1


def record_redis_error():
    METRICS_REGISTRY["redis_errors_total"] = METRICS_REGISTRY.get("redis_errors_total", 0) + 1


def get_metrics() -> Dict[str, Any]:
    global _pending_latencies, _last_snapshot_time
    now = time.monotonic()
    elapsed = max(now - _last_snapshot_time, 1)
    request_rate = METRICS_REGISTRY["http_requests_total"] / max(elapsed, 1)

    avg_latency = sum(_pending_latencies) / max(len(_pending_latencies), 1) if _pending_latencies else 0
    p50_latency = _percentile(_pending_latencies, 50)
    p95_latency = _percentile(_pending_latencies, 95)
    p99_latency = _percentile(_pending_latencies, 99)

    cache_total = METRICS_REGISTRY.get("cache_hits_total", 0) + METRICS_REGISTRY.get("cache_misses_total", 0)
    cache_hit_rate = METRICS_REGISTRY.get("cache_hits_total", 0) / max(cache_total, 1)

    return {
        "uptime_seconds": round(elapsed, 1),
        "http": {
            "requests_total": METRICS_REGISTRY.get("http_requests_total", 0),
            "requests_per_second": round(request_rate, 2),
            "by_status": METRICS_REGISTRY.get("http_requests_by_status", {}),
            "latency_avg_ms": round(avg_latency, 1),
            "latency_p50_ms": round(p50_latency, 1),
            "latency_p95_ms": round(p95_latency, 1),
            "latency_p99_ms": round(p99_latency, 1),
        },
        "agent": {
            "runs_total": METRICS_REGISTRY.get("agent_runs_total", 0),
            "by_status": METRICS_REGISTRY.get("agent_runs_by_status", {}),
            "by_type": METRICS_REGISTRY.get("agent_runs_by_type", {}),
            "token_usage_total": METRICS_REGISTRY.get("agent_token_usage_total", 0),
            "cost_total_usd": round(METRICS_REGISTRY.get("agent_cost_total_usd", 0), 6),
        },
        "database": {
            "connections_active": METRICS_REGISTRY.get("db_connections_active", 0),
            "query_count": METRICS_REGISTRY.get("db_query_count", 0),
        },
        "redis": {
            "connects_total": METRICS_REGISTRY.get("redis_connects_total", 0),
            "errors_total": METRICS_REGISTRY.get("redis_errors_total", 0),
        },
        "cache": {
            "hits": METRICS_REGISTRY.get("cache_hits_total", 0),
            "misses": METRICS_REGISTRY.get("cache_misses_total", 0),
            "hit_rate": round(cache_hit_rate * 100, 1),
        },
        "security": {
            "login_attempts": METRICS_REGISTRY.get("login_attempts_total", 0),
            "login_failures": METRICS_REGISTRY.get("login_failures_total", 0),
            "rate_limit_hits": METRICS_REGISTRY.get("rate_limit_hits_total", 0),
        },
    }


def generate_prometheus_metrics() -> str:
    metrics = get_metrics()

    lines = [
        "# HELP successcore_http_requests_total Total HTTP requests served",
        f"# TYPE successcore_http_requests_total counter",
        f"successcore_http_requests_total {metrics['http']['requests_total']}",
        "",
        "# HELP successcore_agent_runs_total Total agent executions",
        f"# TYPE successcore_agent_runs_total counter",
        f"successcore_agent_runs_total {metrics['agent']['runs_total']}",
        "",
        "# HELP successcore_agent_token_usage_total Total tokens consumed by agents",
        f"# TYPE successcore_agent_token_usage_total counter",
        f"successcore_agent_token_usage_total {metrics['agent']['token_usage_total']}",
        "",
        "# HELP successcore_agent_cost_usd_total Total USD cost of agent runs",
        f"# TYPE successcore_agent_cost_usd_total counter",
        f"successcore_agent_cost_usd_total {metrics['agent']['cost_total_usd']}",
        "",
        "# HELP successcore_http_latency_ms_avg Average HTTP request latency",
        f"# TYPE successcore_http_latency_ms_avg gauge",
        f"successcore_http_latency_ms_avg {metrics['http']['latency_avg_ms']}",
        "",
        "# HELP successcore_db_connections_active Active database connections",
        f"# TYPE successcore_db_connections_active gauge",
        f"successcore_db_connections_active {metrics['database']['connections_active']}",
        "",
        "# HELP successcore_cache_hit_rate Cache hit rate percentage",
        f"# TYPE successcore_cache_hit_rate gauge",
        f"successcore_cache_hit_rate {metrics['cache']['hit_rate']}",
        "",
        "# HELP successcore_login_attempts_total Total login attempts",
        f"# TYPE successcore_login_attempts_total counter",
        f"successcore_login_attempts_total {metrics['security']['login_attempts']}",
        "",
        "# HELP successcore_rate_limit_hits_total Total rate limit hits",
        f"# TYPE successcore_rate_limit_hits_total counter",
        f"successcore_rate_limit_hits_total {metrics['security']['rate_limit_hits']}",
    ]

    for status_bucket, count in metrics["http"]["by_status"].items():
        lines.extend([
            "",
            f"# HELP successcore_http_requests_{status_bucket} HTTP requests by status class",
            f"# TYPE successcore_http_requests_{status_bucket} counter",
            f"successcore_http_requests_{status_bucket} {count}",
        ])

    for agent_type, count in metrics["agent"]["by_type"].items():
        safe_name = agent_type.replace("-", "_").replace(".", "_")
        lines.extend([
            "",
            f"# HELP successcore_agent_runs_{safe_name} Agent runs by type",
            f"# TYPE successcore_agent_runs_{safe_name} counter",
            f"successcore_agent_runs_{safe_name} {count}",
        ])

    return "\n".join(lines) + "\n"


def _percentile(data: list, percentile: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]
