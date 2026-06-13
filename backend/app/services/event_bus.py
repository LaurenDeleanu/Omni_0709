import asyncio
import logging
import json
from typing import Dict, List, Callable, Awaitable, Any

logger = logging.getLogger("successcore.events")

Subscriber = Callable[..., Awaitable[Any]]


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._redis_listener_task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: Subscriber):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Subscriber):
        if event_type in self._subscribers:
            self._subscribers[event_type] = [h for h in self._subscribers[event_type] if h is not handler]

    async def publish(self, event_type: str, **kwargs) -> None:
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        tasks = [h(**kwargs) for h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"Event handler {handlers[i].__name__} failed for {event_type}: {r}")

        await self._publish_redis(event_type, **kwargs)

    def publish_async(self, event_type: str, **kwargs) -> None:
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return

        async def _fire():
            for h in handlers:
                try:
                    await h(**kwargs)
                except Exception as e:
                    logger.error(f"Event handler {h.__name__} failed for {event_type}: {e}")
            await self._publish_redis(event_type, **kwargs)

        asyncio.create_task(_fire())

    async def _publish_redis(self, event_type: str, **kwargs) -> None:
        try:
            from app.core.redis import get_redis
            r = await get_redis()
            if r:
                payload = json.dumps({"event_type": event_type, "data": kwargs}, default=str)
                await r.publish("successcore:events", payload)
        except Exception as e:
            logger.debug(f"Redis event publish failed: {e}")

    async def start_redis_listener(self):
        try:
            from app.core.redis import get_redis
            r = await get_redis()
            if r is None:
                logger.warning("Redis not available, skipping event listener")
                return

            async def _listen():
                pubsub = r.pubsub()
                await pubsub.subscribe("successcore:events")
                logger.info("Event bus Redis listener started on channel successcore:events")
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            event_type = data.get("event_type")
                            event_data = data.get("data", {})
                            if event_type and event_type in self._subscribers:
                                for handler in self._subscribers[event_type]:
                                    try:
                                        await handler(**event_data)
                                    except Exception as e:
                                        logger.error(f"Redis event handler {handler.__name__} failed: {e}")
                        except Exception as e:
                            logger.error(f"Redis event processing error: {e}")

            self._redis_listener_task = asyncio.create_task(_listen())
        except Exception as e:
            logger.warning(f"Failed to start Redis event listener: {e}")

    async def stop_redis_listener(self):
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
            try:
                await self._redis_listener_task
            except asyncio.CancelledError:
                pass


_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus
