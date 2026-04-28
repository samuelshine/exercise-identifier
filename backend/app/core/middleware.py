"""
HTTP middleware: request ID, structured access logging, security headers,
and a hard body-size limit.
"""

import logging
import time
import uuid

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.logging_config import request_id_var

logger = logging.getLogger("app.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assign every request an ID, surface it in logs and the response header.

    If the client (or an upstream proxy) sends X-Request-ID, we honor it —
    that's how a request can be traced across multiple services. Otherwise
    we mint a fresh UUID4.
    """

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = rid

        # Structured access log — one line per request, indexable by status/path.
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
                "client": request.client.host if request.client else None,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Apply browser-side defense-in-depth headers.

    HSTS is only set when running over HTTPS — sending it on plain HTTP
    has no effect and confuses load balancers running TLS termination.
    """

    def __init__(self, app: ASGIApp, *, hsts: bool = True):
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if self.hsts and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Reject requests whose Content-Length exceeds the configured cap before
    the body is read into memory. Prevents an attacker from tying up a
    worker with an oversized payload.

    The cap is only enforced on methods that carry a body. We trust the
    Content-Length header — for chunked transfers without a length, the
    upstream proxy (ALB / nginx) is the right place to enforce the cap.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl is not None:
                try:
                    if int(cl) > self.max_bytes:
                        return JSONResponse(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content={
                                "detail": f"Request body too large (max {self.max_bytes} bytes).",
                                "request_id": request_id_var.get(),
                            },
                        )
                except ValueError:
                    pass  # malformed header — let downstream return 400
        return await call_next(request)
