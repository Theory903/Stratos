# ── Stage 1: Builder ─────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools for packages that need C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy ALL source needed for 'pip install .' in src-layout
COPY data-fabric/pyproject.toml .
COPY data-fabric/src/ ./src/
COPY data-fabric/alembic.ini .
COPY data-fabric/migrations/ ./migrations/

# Install the package and all its dependencies
RUN pip install --no-cache-dir .

# ── Stage 2: Runtime ─────────────────────────────────
FROM python:3.12-slim

# Install runtime C libs (asyncpg needs libpq at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/alembic /usr/local/bin/alembic
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /app/src ./src
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/migrations ./migrations

ENV PYTHONPATH=/app/src

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "data_fabric.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
