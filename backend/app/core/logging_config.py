"""
Logging configuration — JSON in production, human-readable in development.

Every log record includes the current request_id (set by RequestIDMiddleware).
Log aggregators (CloudWatch, Datadog, Loki) can index on `request_id`,
`path`, and `status` to correlate a single request across multiple log lines.
"""

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

# Set per request by RequestIDMiddleware. Default "-" makes log lines outside
# request scope (e.g. startup) clearly distinguishable.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIDFilter(logging.Filter):
    """Inject the current request_id into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(*, json_logs: bool, level: str = "INFO") -> None:
    """
    Configure the root logger. Idempotent — safe to call from lifespan.

    json_logs=True is the right setting for any deployed environment
    (the structure is what makes logs queryable). Local dev keeps the
    classic single-line format because humans read those.
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIDFilter())

    if json_logs:
        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(request_id)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet noisy libraries — they're useful at DEBUG, never at INFO.
    for noisy in ("httpx", "httpcore", "chromadb", "uvicorn.access"):
        logging.getLogger(noisy).setLevel("WARNING")
