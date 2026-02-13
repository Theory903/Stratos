FROM python:3.12-slim AS builder
WORKDIR /app
COPY data-fabric/pyproject.toml .
RUN pip install --no-cache-dir .
COPY data-fabric/src/ ./src/

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src ./src
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "data_fabric.api.app:create_app", "--host", "0.0.0.0", "--port", "8001", "--factory"]
