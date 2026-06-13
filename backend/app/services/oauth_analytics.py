import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger("successcore.oauth_analytics")

_oauth_usage = defaultdict(lambda: {"calls": 0, "errors": 0, "last_used": None})


def record_oauth_call(client_id: str, status_code: int):
    _oauth_usage[client_id]["calls"] += 1
    _oauth_usage[client_id]["last_used"] = datetime.now(timezone.utc).isoformat()
    if status_code >= 400:
        _oauth_usage[client_id]["errors"] += 1


def get_oauth_stats(client_id: str = "") -> dict:
    if client_id:
        return {"client_id": client_id, **_oauth_usage.get(client_id, {"calls": 0, "errors": 0})}
    all_stats = {}
    for cid, stats in _oauth_usage.items():
        all_stats[cid] = dict(stats)
    return {"clients": all_stats, "total_apps": len(_oauth_usage)}
