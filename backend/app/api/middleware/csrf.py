import secrets
import hashlib
import time
import hmac
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_TTL_SECONDS = 28800

def _generate_csrf_token(session_id: str) -> str:
    raw = f"{session_id}:{int(time.time())}"
    sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{raw}:{sig}"

def _verify_csrf_token(token: str, session_id: str, max_age: int = CSRF_TTL_SECONDS) -> bool:
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return False
        payload, sig = parts
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        payload_parts = payload.split(":", 1)
        if len(payload_parts) != 2 or payload_parts[0] != session_id:
            return False
        token_time = int(payload_parts[1])
        if time.time() - token_time > max_age:
            return False
        return True
    except Exception:
        return False

class CSRFTokenManager:
    def get_or_create_token(self, request: Request) -> str:
        session_id = request.cookies.get("access_token") or secrets.token_hex(24)
        return _generate_csrf_token(session_id)

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        cookie_token = request.cookies.get("access_token")
        if not cookie_token:
            return await call_next(request)

        if settings.DEBUG_MODE and not auth_header:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in ["/api/v1/ai/copilot/stream", "/api/v1/ai/copilot", "/api/v1/omni"]):
            return await call_next(request)

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        if origin and settings.FRONTEND_URL not in origin and "localhost" not in origin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Origin header.",
            )
        if not origin and referer and settings.FRONTEND_URL not in referer and "localhost" not in referer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Referer header.",
            )

        csrf_header = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")
        if not csrf_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing X-CSRF-Token header. CSRF protection is active for cookie-based sessions.",
            )

        if not _verify_csrf_token(csrf_header, cookie_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired CSRF token.",
            )

        return await call_next(request)
