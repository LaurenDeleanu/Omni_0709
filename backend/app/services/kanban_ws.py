import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("successcore.kanban")

_clients: Dict[str, Set[WebSocket]] = {}


async def connect_kanban(board_id: str, ws: WebSocket):
    await ws.accept()
    if board_id not in _clients:
        _clients[board_id] = set()
    _clients[board_id].add(ws)


def disconnect_kanban(board_id: str, ws: WebSocket):
    if board_id in _clients:
        _clients[board_id].discard(ws)
        if not _clients[board_id]:
            del _clients[board_id]


async def broadcast_kanban_change(board_id: str, event: str, data: dict, sender: WebSocket = None):
    if board_id not in _clients:
        return
    payload = json.dumps({"event": event, "data": data}, default=str)
    dead: list = []
    for ws in _clients[board_id]:
        if ws is sender:
            continue
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        disconnect_kanban(board_id, ws)
