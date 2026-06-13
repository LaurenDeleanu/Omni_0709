import asyncio
import logging
from typing import Dict

logger = logging.getLogger("successcore.concurrency")

MAX_CONCURRENT_RUNS = 10
PER_TENANT_MAX = 3
ACQUIRE_TIMEOUT_SECONDS = 30

_active_runs: Dict[str, int] = {}
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
_tenant_semaphores: Dict[str, asyncio.Semaphore] = {}
_lock = asyncio.Lock()


async def acquire_run_slot(tenant_id: str) -> bool:
    async with _lock:
        if tenant_id not in _tenant_semaphores:
            _tenant_semaphores[tenant_id] = asyncio.Semaphore(PER_TENANT_MAX)

    tenant_sem = _tenant_semaphores[tenant_id]
    if tenant_sem.locked() and _semaphore.locked():
        return False

    try:
        await asyncio.wait_for(_semaphore.acquire(), timeout=ACQUIRE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout acquiring global semaphore for tenant {tenant_id}")
        return False

    try:
        await asyncio.wait_for(tenant_sem.acquire(), timeout=ACQUIRE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        _semaphore.release()
        logger.warning(f"Timeout acquiring tenant semaphore for tenant {tenant_id}")
        return False

    _active_runs[tenant_id] = _active_runs.get(tenant_id, 0) + 1
    return True


def release_run_slot(tenant_id: str):
    _semaphore.release()
    if tenant_id in _tenant_semaphores:
        _tenant_semaphores[tenant_id].release()
    _active_runs[tenant_id] = max(0, _active_runs.get(tenant_id, 1) - 1)


def get_concurrency_status() -> dict:
    return {
        "active_runs": sum(_active_runs.values()),
        "per_tenant": dict(_active_runs),
        "total_limit": MAX_CONCURRENT_RUNS,
        "per_tenant_limit": PER_TENANT_MAX,
    }
