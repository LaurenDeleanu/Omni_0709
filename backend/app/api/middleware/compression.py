import gzip
import io
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class CompressionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        accept_encoding = request.headers.get("Accept-Encoding", "")
        content_type = response.headers.get("Content-Type", "")
        body = b""

        if response.status_code >= 300 or "text/event-stream" in content_type:
            return response

        if not isinstance(response, Response):
            return response

        if hasattr(response, "body"):
            body = response.body if isinstance(response.body, bytes) else response.body.encode()
        elif hasattr(response, "raw_headers"):
            body = b""

        if len(body) < 1024:
            return response

        if "br" in accept_encoding:
            try:
                import brotli
                compressed = brotli.compress(body, quality=4)
                response.body = compressed
                response.headers["Content-Encoding"] = "br"
                response.headers["Content-Length"] = str(len(compressed))
            except ImportError:
                buf = io.BytesIO()
                with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
                    gz.write(body)
                compressed = buf.getvalue()
                response.body = compressed
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(compressed))
        elif "gzip" in accept_encoding:
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
                gz.write(body)
            compressed = buf.getvalue()
            response.body = compressed
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed))

        return response
