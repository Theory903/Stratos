"""Orchestrator service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "ORCH_", "env_file": ".env"}

    host: str = "0.0.0.0"
    port: int = 8005
    debug: bool = False

    # LLM
    llm_provider: str = "openai"  # openai, anthropic, local
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Downstream services
    data_fabric_url: str = "http://localhost:8001"
    engines_java_url: str = "http://localhost:8002"
    ml_service_url: str = "http://localhost:8003"
    nlp_service_url: str = "http://localhost:8004"
