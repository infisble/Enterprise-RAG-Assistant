import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_context import request_id_ctx

logger = logging.getLogger("api.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000)
            request_id_ctx.reset(token)
            if "response" in locals():
                response.headers["x-request-id"] = request_id
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                },
            )
