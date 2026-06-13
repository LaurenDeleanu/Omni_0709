import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("successcore.body_limit")

DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024
EXEMPT_PATHS = [
    "/api/v1/imports/",
    "/api/v1/agents/upload",
    "/api/v1/chat/upload",
]


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size_bytes: int = DEFAULT_MAX_BODY_SIZE):
        super().__init__(app)
        self.max_size = max_size_bytes

    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS", "DELETE"):
            return await call_next(request)

        path = request.url.path
        for exempt in EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body exceeds maximum size of {self.max_size // (1024*1024)}MB.",
                    )
            except (ValueError, TypeError):
                pass

        return await call_next(request)
