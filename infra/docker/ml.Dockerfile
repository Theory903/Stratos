FROM python:3.12-slim AS builder
WORKDIR /app
COPY ml/pyproject.toml .
RUN pip install --no-cache-dir .
COPY ml/src/ ./src/

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src ./src
EXPOSE 8003
CMD ["python", "-m", "uvicorn", "stratos_ml.api.app:create_app", "--host", "0.0.0.0", "--port", "8003", "--factory"]
