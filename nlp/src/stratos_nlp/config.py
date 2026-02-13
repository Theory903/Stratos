"""NLP service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "NLP_", "env_file": ".env"}

    host: str = "0.0.0.0"
    port: int = 8004
    debug: bool = False
    embedding_model: str = "all-MiniLM-L6-v2"
    sentiment_model: str = "ProsusAI/finbert"
    pgvector_url: str = "postgresql+asyncpg://stratos:changeme@localhost:5432/stratos"
