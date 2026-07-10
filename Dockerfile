# syntax=docker/dockerfile:1

# -- Build stage --
FROM python:3.13-slim AS builder

ARG PLOIDY_VERSION=0.4.0

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src/ src/

RUN python -m pip install --no-cache-dir --prefix=/install \
    ".[api,dashboard,metrics,redis,cli]"

# -- Runtime stage --
FROM python:3.13-slim

ARG PLOIDY_VERSION=0.4.0
ARG VCS_REF=unknown

LABEL org.opencontainers.image.title="Ploidy" \
      org.opencontainers.image.source="https://github.com/heznpc/PLOIDY" \
      org.opencontainers.image.version="${PLOIDY_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MIT"

RUN groupadd --system ploidy && useradd --system --gid ploidy ploidy

COPY --from=builder /install /usr/local

WORKDIR /app

RUN mkdir /data && chown ploidy:ploidy /data

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLOIDY_TRANSPORT=streamable-http \
    PLOIDY_PORT=8765 \
    PLOIDY_DB_PATH=/data/ploidy.db \
    PLOIDY_LOG_LEVEL=INFO \
    PLOIDY_MAX_CONTEXT_DOCS=10 \
    PLOIDY_MAX_CONTEXT_TOKENS=20000 \
    PLOIDY_RATE_CAPACITY=20 \
    PLOIDY_RATE_PER_SEC=1 \
    PLOIDY_RETENTION_DAYS=30

EXPOSE 8765

VOLUME /data

USER ploidy

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3)"

CMD ["python", "-m", "ploidy"]
