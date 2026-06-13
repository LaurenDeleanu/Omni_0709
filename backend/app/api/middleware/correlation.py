import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import request_id_var, tenant_id_var
import jwt

logger = logging.getLogger("successcore.correlation")

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Extract tenant_id from auth header if possible (best effort without blocking)
        tenant_id = "-"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Only decode without verification just to extract tenant_id for logging
                payload = jwt.decode(token, options={"verify_signature": False})
                app_metadata = payload.get("https://successcore.com/app_metadata", {})
                tenant_id = app_metadata.get("tenant_id") or payload.get("tenant_id", "default")
            except Exception:
                pass
                
        request_token = request_id_var.set(request_id)
        tenant_token = tenant_id_var.set(tenant_id)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(request_token)
            tenant_id_var.reset(tenant_token)
