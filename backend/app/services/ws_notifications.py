import asyncio
import json
import logging
from typing import Dict, Set, List
from fastapi import WebSocket

logger = logging.getLogger("successcore.ws_notif")

_notification_clients: Dict[str, Set[WebSocket]] = {}


async def connect_notifications(user_id: str, ws: WebSocket):
    await ws.accept()
    if user_id not in _notification_clients:
        _notification_clients[user_id] = set()
    _notification_clients[user_id].add(ws)


def disconnect_notifications(user_id: str, ws: WebSocket):
    if user_id in _notification_clients:
        _notification_clients[user_id].discard(ws)
        if not _notification_clients[user_id]:
            del _notification_clients[user_id]


async def push_notification_to_user(user_id: str, notification_data: dict) -> int:
    if user_id not in _notification_clients:
        return 0
    payload = json.dumps({"type": "notification", "data": notification_data}, default=str)
    dead = []
    sent = 0
    for ws in _notification_clients[user_id]:
        try:
            await ws.send_text(payload)
            sent += 1
        except Exception:
            dead.append(ws)
    for ws in dead:
        disconnect_notifications(user_id, ws)
    return sent
