# app/core/task_queue.py — Redis-backed background task queue
# Replaces FastAPI BackgroundTasks with persistent, retryable, observable queue.
import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Coroutine, Optional
import redis.asyncio as redis

from app.core.redis import get_redis

logger = logging.getLogger("successcore.tasks")

TASK_QUEUE_KEY = "successcore:task_queue"
TASK_STATUS_PREFIX = "successcore:task_status:"
TASK_MAX_RETRIES = 3
POLL_INTERVAL = 1  # integer — required by older Redis (3.x)

_task_registry: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
_worker_running = False


def register_task(name: str, fn: Callable[..., Coroutine[Any, Any, Any]]):
    _task_registry[name] = fn


async def enqueue(task_name: str, args: Optional[dict] = None, tenant_id: str = "") -> str:
    task_id = uuid.uuid4().hex
    payload = {
        "task_id": task_id,
        "task_name": task_name,
        "args": args or {},
        "tenant_id": tenant_id,
        "retries": 0,
    }
    r = await get_redis()
    await r.rpush(TASK_QUEUE_KEY, json.dumps(payload))
    await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({"status": "pending", "progress": 0}))
    logger.info(f"Task enqueued: {task_name}#{task_id}")
    return task_id


async def get_task_status(task_id: str) -> dict:
    r = await get_redis()
    raw = await r.get(f"{TASK_STATUS_PREFIX}{task_id}")
    if raw:
        return json.loads(raw)
    return {"status": "not_found"}


async def start_worker():
    global _worker_running
    if _worker_running:
        return
    _worker_running = True
    asyncio.create_task(_worker_loop())
    logger.info("Task queue worker started")


async def stop_worker():
    global _worker_running
    _worker_running = False


async def _worker_loop():
    while _worker_running:
        try:
            r = await get_redis()
            result = await r.blpop(TASK_QUEUE_KEY, timeout=POLL_INTERVAL)
            if result is None:
                continue
            _, raw = result
            payload = json.loads(raw)
            await _execute_task(payload, r)
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await asyncio.sleep(1)


async def _execute_task(payload: dict, r: redis.Redis):
    task_id = payload["task_id"]
    task_name = payload["task_name"]
    fn = _task_registry.get(task_name)

    if not fn:
        logger.error(f"Unknown task: {task_name}")
        await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({"status": "failed", "error": f"Unknown task: {task_name}"}))
        return

    await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({"status": "running", "progress": 0}))

    def progress_callback(status: str, data: dict):
        asyncio.create_task(_update_status(task_id, status, data))

    try:
        result = await fn(task_id=task_id, progress_callback=progress_callback, **payload.get("args", {}))
        await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({"status": "completed", "result": result}))
        logger.info(f"Task completed: {task_name}#{task_id}")
    except Exception as e:
        retries = payload.get("retries", 0) + 1
        logger.error(f"Task failed ({task_name}#{task_id}, retry {retries}/{TASK_MAX_RETRIES}): {e}")
        if retries < TASK_MAX_RETRIES:
            payload["retries"] = retries
            backoff = 2 ** retries
            await asyncio.sleep(backoff)
            await r.rpush(TASK_QUEUE_KEY, json.dumps(payload))
        else:
            await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({
                "status": "failed",
                "error": "La tarea fallo durante el procesamiento. Contacta al soporte.",
                "retries": retries
            }))


async def _update_status(task_id: str, status: str, data: dict):
    try:
        r = await get_redis()
        current = json.loads(await r.get(f"{TASK_STATUS_PREFIX}{task_id}") or "{}")
        current["status"] = status
        current.update(data)
        await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps(current))
    except Exception:
        pass
