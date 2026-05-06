from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("omnisight.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        start = time.time()

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start) * 1000, 2)

            log_payload = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
            logger.info(json.dumps(log_payload))
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            duration_ms = round((time.time() - start) * 1000, 2)
            log_payload = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
            }
            logger.exception(json.dumps(log_payload))
            raise