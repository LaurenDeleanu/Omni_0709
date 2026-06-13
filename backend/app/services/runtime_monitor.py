import logging
import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field

logger = logging.getLogger("successcore.agent_runtime_v2")


@dataclass
class ExecutorStats:
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    cancelled_executions: int = 0
    throttled_executions: int = 0
    total_latency_ms: float = 0.0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    last_execution_at: float = 0.0
    last_error: Optional[str] = None


executor_stats = ExecutorStats()


def record_execution(result: Dict[str, Any], latency_ms: int):
    executor_stats.total_executions += 1
    executor_stats.total_latency_ms += latency_ms
    executor_stats.last_execution_at = time.monotonic()

    status = result.get("status", "unknown")
    if status in ("success", "completed"):
        executor_stats.successful_executions += 1
    elif status == "throttled":
        executor_stats.throttled_executions += 1
    elif status == "cancelled":
        executor_stats.cancelled_executions += 1
    else:
        executor_stats.failed_executions += 1

    tokens = result.get("token_usage", 0) or result.get("tokens_used", 0)
    cost = result.get("cost_usd", 0.0)
    executor_stats.total_tokens_used += tokens
    executor_stats.total_cost_usd += cost


def get_executor_health() -> Dict[str, Any]:
    total = max(executor_stats.total_executions, 1)
    return {
        "total_executions": executor_stats.total_executions,
        "success_rate_pct": round(executor_stats.successful_executions / total * 100, 1),
        "failure_rate_pct": round(executor_stats.failed_executions / total * 100, 1),
        "cancellation_rate_pct": round(executor_stats.cancelled_executions / total * 100, 1),
        "avg_latency_ms": round(executor_stats.total_latency_ms / total, 1),
        "total_tokens_used": executor_stats.total_tokens_used,
        "total_cost_usd": round(executor_stats.total_cost_usd, 6),
        "last_execution_ago_seconds": round(time.monotonic() - executor_stats.last_execution_at, 1) if executor_stats.last_execution_at > 0 else -1,
        "healthy": executor_stats.failed_executions < total * 0.2,
    }


class HeartbeatTracker:
    def __init__(self):
        self._heartbeats: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def beat(self, run_id: str):
        async with self._lock:
            self._heartbeats[run_id] = time.monotonic()

    async def get_stale(self, timeout_seconds: int = 120) -> List[str]:
        async with self._lock:
            now = time.monotonic()
            stale = [rid for rid, ts in self._heartbeats.items() if now - ts > timeout_seconds]
            for rid in stale:
                self._heartbeats.pop(rid, None)
                logger.warning(f"Stale execution detected: run_id={rid[:8]}")
            return stale

    async def remove(self, run_id: str):
        async with self._lock:
            self._heartbeats.pop(run_id, None)

    @property
    def active_count(self) -> int:
        return len(self._heartbeats)


heartbeat_tracker = HeartbeatTracker()


async def start_heartbeat_monitor(interval_seconds: int = 60):
    async def _monitor():
        while True:
            await asyncio.sleep(interval_seconds)
            stale = await heartbeat_tracker.get_stale()
            if stale:
                logger.warning(f"Heartbeat monitor detected {len(stale)} stale executions")
    asyncio.create_task(_monitor())
    logger.info(f"Heartbeat monitor started (interval={interval_seconds}s)")


class BackgroundTaskSupervisor:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register(self, name: str, coro_or_factory: Callable[[], Awaitable[Any]], restart_on_failure: bool = True):
        async with self._lock:
            self._tasks[name] = {
                "factory": coro_or_factory,
                "task": None,
                "restart_on_failure": restart_on_failure,
                "status": "registered",
                "last_started": 0.0,
                "last_error": None,
                "restart_count": 0,
            }

    async def start_all(self):
        async with self._lock:
            for name, info in self._tasks.items():
                if info["task"] is None or info["task"].done():
                    info["status"] = "starting"
                    info["last_started"] = time.monotonic()
                    task = asyncio.create_task(self._run_supervised(name, info))
                    info["task"] = task
                    logger.info(f"Supervisor: started task '{name}'")

    async def _run_supervised(self, name: str, info: Dict[str, Any]):
        while True:
            try:
                await info["factory"]()
                info["status"] = "completed"
                logger.info(f"Supervisor: task '{name}' completed normally")
                break
            except asyncio.CancelledError:
                info["status"] = "cancelled"
                logger.info(f"Supervisor: task '{name}' cancelled")
                break
            except Exception as e:
                info["status"] = "failed"
                info["last_error"] = str(e)[:500]
                info["restart_count"] += 1
                logger.error(f"Supervisor: task '{name}' failed (restart #{info['restart_count']}): {e}")
                if info["restart_on_failure"]:
                    delay = min(2 ** info["restart_count"], 60)
                    logger.info(f"Supervisor: restarting '{name}' in {delay}s")
                    await asyncio.sleep(delay)
                    info["status"] = "restarting"
                    info["last_started"] = time.monotonic()
                else:
                    break

    async def stop_all(self):
        async with self._lock:
            for name, info in self._tasks.items():
                task = info.get("task")
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    info["status"] = "stopped"

    async def get_status(self) -> Dict[str, Any]:
        async with self._lock:
            statuses = {}
            for name, info in self._tasks.items():
                statuses[name] = {
                    "status": info["status"],
                    "last_started_ago_seconds": round(time.monotonic() - info["last_started"], 1) if info["last_started"] > 0 else -1,
                    "restart_count": info["restart_count"],
                    "last_error": info["last_error"][:200] if info["last_error"] else None,
                }
            return statuses


_task_supervisor = BackgroundTaskSupervisor()


def get_task_supervisor() -> BackgroundTaskSupervisor:
    return _task_supervisor
