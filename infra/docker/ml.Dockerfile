# ── Stage 1: Builder ─────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy ALL source needed for 'pip install .' in src-layout
COPY ml/pyproject.toml .
COPY ml/src/ ./src/

# torch is large — no-cache avoids bloating layer with pip cache
RUN pip install --no-cache-dir .

# ── Stage 2: Runtime ─────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /app/src ./src

ENV PYTHONPATH=/app/src

EXPOSE 8003
CMD ["python", "-m", "uvicorn", "stratos_ml.api.app:create_app", "--host", "0.0.0.0", "--port", "8003", "--factory"]
