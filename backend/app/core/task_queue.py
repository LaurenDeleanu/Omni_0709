# app/core/task_queue.py — Redis Streams-backed background task queue
# Replaces FastAPI BackgroundTasks with persistent, retryable, observable queue.
# Uses Redis Streams with consumer groups for at-least-once delivery.
import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Coroutine, Optional
import redis.asyncio as redis

from app.core.redis import get_redis

logger = logging.getLogger("successcore.tasks")

STREAM_KEY = "successcore:task_stream"
GROUP_NAME = "task_workers"
CONSUMER_NAME = f"worker_{uuid.uuid4().hex[:8]}"
TASK_STATUS_PREFIX = "successcore:task_status:"
TASK_MAX_RETRIES = 3
POLL_INTERVAL = 2
DEAD_LETTER_STREAM = "successcore:task_stream_dlq"

_task_registry: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
_worker_running = False


def register_task(name: str, fn: Callable[..., Coroutine[Any, Any, Any]]):
    _task_registry[name] = fn


async def _ensure_consumer_group(r: redis.Redis):
    try:
        await r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


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
    await _ensure_consumer_group(r)
    await r.xadd(STREAM_KEY, {"payload": json.dumps(payload)}, maxlen=10000)
    await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({"status": "pending", "progress": 0}))
    logger.info(f"Task enqueued: {task_name}#{task_id}")
    return task_id


async def get_task_status(task_id: str) -> dict:
    r = await get_redis()
    raw = await r.get(f"{TASK_STATUS_PREFIX}{task_id}")
    if raw:
        return json.loads(raw)
    return {"status": "not_found"}


async def get_pending_count() -> int:
    try:
        r = await get_redis()
        info = await r.xinfo_groups(STREAM_KEY)
        for g in info:
            if g["name"] == GROUP_NAME:
                return int(g["pending"])
    except Exception:
        pass
    return 0


async def start_worker():
    global _worker_running
    if _worker_running:
        return
    _worker_running = True
    asyncio.create_task(_worker_loop())
    logger.info(f"Task queue worker started (consumer={CONSUMER_NAME})")


async def stop_worker():
    global _worker_running
    _worker_running = False


async def _worker_loop():
    r = await get_redis()
    await _ensure_consumer_group(r)

    while _worker_running:
        try:
            # Read pending messages first (recovery after crash)
            pending = await r.xpending_range(STREAM_KEY, GROUP_NAME, min="-", max="+", count=10)
            pending_ids = [p["message_id"] for p in pending]

            # Read new messages from stream
            streams = await r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=1,
                block=POLL_INTERVAL * 1000,
            )

            # Process pending recovery messages
            for msg_id in pending_ids:
                try:
                    result = await r.xrange(STREAM_KEY, min=msg_id, max=msg_id, count=1)
                    if result:
                        _, raw = result[0]
                        payload = json.loads(raw.get("payload", "{}"))
                        await _execute_task(payload, r)
                        await r.xack(STREAM_KEY, GROUP_NAME, msg_id)
                except Exception as e:
                    logger.error(f"Pending message recovery failed: {e}")

            # Process new messages
            for stream_name, messages in streams:
                for msg_id, raw in messages:
                    try:
                        payload = json.loads(raw.get("payload", "{}"))
                        await _execute_task(payload, r)
                        await r.xack(STREAM_KEY, GROUP_NAME, msg_id)
                    except Exception as e:
                        logger.error(f"Task processing failed: {e}", exc_info=True)

        except redis.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await asyncio.sleep(1)


async def _execute_task(payload: dict, r: redis.Redis):
    task_id = payload["task_id"]
    task_name = payload["task_name"]
    fn = _task_registry.get(task_name)

    if not fn:
        logger.error(f"Unknown task: {task_name}")
        await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({
            "status": "failed", "error": f"Unknown task: {task_name}"
        }))
        return

    await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({"status": "running", "progress": 0}))

    def progress_callback(status: str, data: dict):
        asyncio.create_task(_update_status(task_id, status, data))

    try:
        result = await fn(task_id=task_id, progress_callback=progress_callback, **payload.get("args", {}))
        await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({
            "status": "completed", "result": result
        }))
        logger.info(f"Task completed: {task_name}#{task_id}")
    except Exception as e:
        retries = payload.get("retries", 0) + 1
        logger.error(f"Task failed ({task_name}#{task_id}, retry {retries}/{TASK_MAX_RETRIES}): {e}")
        if retries < TASK_MAX_RETRIES:
            payload["retries"] = retries
            backoff = 2 ** retries
            await asyncio.sleep(backoff)
            await r.xadd(STREAM_KEY, {"payload": json.dumps(payload)}, maxlen=10000)
            await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({
                "status": "retrying", "retries": retries
            }))
        else:
            await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps({
                "status": "failed",
                "error": str(e),
                "retries": retries
            }))
            # Push to dead-letter stream for manual inspection
            await r.xadd(DEAD_LETTER_STREAM, {
                "payload": json.dumps(payload),
                "error": str(e)[:1000],
                "failed_at": str(asyncio.get_event_loop().time()),
            }, maxlen=1000)


async def _update_status(task_id: str, status: str, data: dict):
    try:
        r = await get_redis()
        current = json.loads(await r.get(f"{TASK_STATUS_PREFIX}{task_id}") or "{}")
        current["status"] = status
        current.update(data)
        await r.set(f"{TASK_STATUS_PREFIX}{task_id}", json.dumps(current))
    except Exception:
        pass
