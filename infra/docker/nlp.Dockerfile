# ── Stage 1: Builder ─────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy ALL source needed for 'pip install .' in src-layout
COPY nlp/pyproject.toml .
COPY nlp/src/ ./src/

RUN pip install --no-cache-dir .

# Download spaCy model at build time so the runtime image is self-contained
RUN python -m spacy download en_core_web_sm

# ── Stage 2: Runtime ─────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /app/src ./src

# spaCy and HuggingFace model cache directories
ENV PYTHONPATH=/app/src
ENV TRANSFORMERS_CACHE=/cache
ENV HF_HOME=/cache

EXPOSE 8004
CMD ["python", "-m", "uvicorn", "stratos_nlp.api.app:create_app", "--host", "0.0.0.0", "--port", "8004", "--factory"]
