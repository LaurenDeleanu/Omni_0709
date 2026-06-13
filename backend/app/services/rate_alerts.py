import time
import logging
from typing import Dict, List

logger = logging.getLogger("successcore.rate_alert")

_alert_counts: Dict[str, dict] = {}
ALERT_THRESHOLD = 10
ALERT_COOLDOWN = 300


def record_rate_limit_hit(client_key: str, path: str) -> dict:
    now = time.monotonic()
    full_key = f"{client_key}:{path}"
    if full_key not in _alert_counts:
        _alert_counts[full_key] = {"count": 0, "first_seen": now, "last_seen": now}
    
    entry = _alert_counts[full_key]
    entry["count"] += 1
    entry["last_seen"] = now

    if entry["count"] >= ALERT_THRESHOLD and (now - entry.get("last_alerted", 0)) > ALERT_COOLDOWN:
        entry["last_alerted"] = now
        logger.warning(f"Rate limit alert: {full_key} hit {entry['count']} times")
        return {"alert": True, "key": client_key, "path": path, "count": entry["count"]}
    
    return {"alert": False}


def get_rate_limit_alerts() -> List[dict]:
    now = time.monotonic()
    alerts = []
    for key, data in _alert_counts.items():
        if data["count"] >= ALERT_THRESHOLD:
            alerts.append({"key": key, "count": data["count"], "last_seen": data["last_seen"]})
    return sorted(alerts, key=lambda a: a["count"], reverse=True)[:20]


def reset_rate_limit_alerts():
    _alert_counts.clear()
