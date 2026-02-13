"""Service configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Data Fabric configuration — loaded from env vars / .env file."""

    model_config = {"env_prefix": "DF_", "env_file": ".env"}

    # Database
    postgres_url: str = "postgresql+asyncpg://stratos:changeme@localhost:5432/stratos"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Kafka
    kafka_brokers: str = "localhost:9092"

    # Object Storage
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "stratos-data"

    # Service
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
