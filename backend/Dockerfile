# syntax=docker/dockerfile:1.7

# ─── Builder ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps for asyncpg / chromadb wheels that occasionally need them.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ─── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Non-root user — never run uvicorn as root.
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=app:app . .

USER app

EXPOSE 8000

# Containers should die fast and predictably — uvicorn handles SIGTERM cleanly,
# no need for a wrapper. Workers default to 1; scale by running multiple
# containers behind a load balancer instead.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]

# /livez is the liveness probe — does not touch external deps.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/livez', timeout=3).status==200 else 1)"
