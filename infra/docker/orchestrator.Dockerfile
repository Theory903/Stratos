FROM python:3.12-slim AS builder
WORKDIR /app
COPY orchestrator/pyproject.toml .
RUN pip install --no-cache-dir .
COPY orchestrator/src/ ./src/

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src ./src
EXPOSE 8005
CMD ["python", "-m", "uvicorn", "stratos_orchestrator.api.app:create_app", "--host", "0.0.0.0", "--port", "8005", "--factory"]
