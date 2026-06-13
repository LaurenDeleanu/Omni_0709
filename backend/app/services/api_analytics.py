import time
import json
import logging
from typing import Dict, Any
from collections import defaultdict
import threading

logger = logging.getLogger("successcore.analytics")

_analytics_lock = threading.Lock()
_route_stats: Dict[str, dict] = defaultdict(lambda: {
    "count": 0,
    "total_latency_ms": 0,
    "errors_4xx": 0,
    "errors_5xx": 0,
    "last_called": "",
})
_client_stats: Dict[str, dict] = defaultdict(lambda: {"count": 0, "last_ip": ""})


def record_request(method: str, path: str, status_code: int, latency_ms: int, client_ip: str):
    key = f"{method} {path}"
    with _analytics_lock:
        s = _route_stats[key]
        s["count"] += 1
        s["total_latency_ms"] += latency_ms
        if 400 <= status_code < 500:
            s["errors_4xx"] += 1
        elif status_code >= 500:
            s["errors_5xx"] += 1
        c = _client_stats[client_ip]
        c["count"] += 1
        c["last_ip"] = client_ip


def get_analytics() -> dict:
    with _analytics_lock:
        routes = []
        total_requests = 0
        for key, s in _route_stats.items():
            if s["count"] == 0:
                continue
            routes.append({
                "route": key,
                "count": s["count"],
                "avg_latency_ms": round(s["total_latency_ms"] / s["count"], 1) if s["count"] else 0,
                "error_4xx": s["errors_4xx"],
                "error_5xx": s["errors_5xx"],
                "error_rate": round((s["errors_4xx"] + s["errors_5xx"]) / max(s["count"], 1) * 100, 2),
            })
            total_requests += s["count"]
        routes.sort(key=lambda r: r["count"], reverse=True)
        return {
            "total_requests": total_requests,
            "routes": routes[:50],
            "unique_clients": len(_client_stats),
        }


def reset_analytics():
    with _analytics_lock:
        _route_stats.clear()
        _client_stats.clear()
