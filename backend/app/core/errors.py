"""
Application-wide exception handlers.

In production, an unhandled exception responds with a generic 500 and the
request_id — the trace is in the logs, never on the wire. In development
we still surface the exception class so the developer sees what blew up
without leaving the terminal.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette import status

from app.core.config import Settings
from app.core.logging_config import request_id_var

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Too many requests. Please slow down and try again shortly.",
                "request_id": request_id_var.get(),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = request_id_var.get()
        # Always log the full exception — that's the only place tracebacks
        # should ever appear once we're in production.
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)

        if settings.is_production:
            detail = "Internal server error."
        else:
            detail = f"{exc.__class__.__name__}: {exc}"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail, "request_id": rid},
        )
