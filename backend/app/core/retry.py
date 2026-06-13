import asyncio
import random
import logging
from functools import wraps
from typing import Type, Tuple, Callable, Awaitable, Any

logger = logging.getLogger("successcore.retry")

RETRYABLE_OPENAI_EXCEPTIONS: Tuple[Type[BaseException], ...] = ()
try:
    import openai
    RETRYABLE_OPENAI_EXCEPTIONS = (
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.InternalServerError,
    )
except ImportError:
    pass


def async_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[BaseException], ...] | None = None,
):
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_OPENAI_EXCEPTIONS

    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Retry exhausted after {max_retries} attempts for {func.__name__}: {e}"
                        )
                        raise
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    if jitter:
                        delay *= 0.75 + random.random() * 0.5
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} in {delay:.1f}s for {func.__name__}: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(delay)
            if last_exception:
                raise last_exception
            raise RuntimeError("async_retry: unreachable")

        return wrapper

    return decorator
