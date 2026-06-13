import logging
import traceback
import time
import os
from typing import Dict, Any, Optional

logger = logging.getLogger("successcore.error_tracker")


def capture_error_context(
    error: Exception,
    endpoint: str = "",
    user_id: str = "",
    tenant_id: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    stack = traceback.format_exc()
    tb = traceback.extract_tb(error.__traceback__)
    source_file = tb[-1].filename.replace("\\", "/") if tb else ""
    source_line = tb[-1].lineno if tb else 0
    func_name = tb[-1].name if tb else ""

    error_context = {
        "type": type(error).__name__,
        "message": str(error)[:500],
        "source_file": source_file.split("app/")[-1] if "app/" in source_file else source_file,
        "source_line": source_line,
        "function": func_name,
        "endpoint": endpoint,
        "user_id": user_id[:16] if user_id else "",
        "tenant_id": tenant_id,
        "timestamp": time.time(),
        "stack_trace": stack[:5000],
        "extra": extra or {},
    }

    logger.error(
        f"ERROR_TRACKER | {error_context['type']} in {error_context['function']} "
        f"at {error_context['source_file']}:{source_line} | {str(error)[:200]}"
    )

    try:
        from app.core.redis import get_redis
        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            from app.core.redis import get_redis
            import json

            async def _store():
                r = await get_redis()
                if r:
                    import json as _json
                    await r.lpush("error_tracker", _json.dumps(error_context, default=str))
                    await r.ltrim("error_tracker", 0, 999)

            try:
                _asyncio.ensure_future(_store())
            except Exception:
                pass
    except Exception:
        pass

    return error_context


def error_boundary(fn=None, *, default_return=None, reraise=False):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                capture_error_context(e, endpoint=getattr(func, "__name__", ""), extra={"args_count": len(args)})
                if reraise:
                    raise
                return default_return
        return wrapper
    if fn is not None:
        return decorator(fn)
    return decorator
