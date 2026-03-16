"""Orchestrator configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Orchestrator settings."""
    
    port: int = 8005
    debug: bool = False
    
    # Service URLs
    data_fabric_url: str = "http://localhost:8000/api/v1"
    data_fabric_v2_url: str = "http://localhost:8000/api/v2"
    ml_service_url: str = "http://localhost:8003/ml"
    nlp_service_url: str = "http://localhost:8004/nlp"
    
    # LLM Config
    llm_provider: str = "ollama"  # openai, anthropic, ollama
    ollama_model: str = "kimi-k2.5:cloud"
    openai_model: str = "gpt-4-turbo-preview"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_model: str = "moonshotai/kimi-k2-instruct-0905"
    groq_api_key: str | None = None
    groq_api_base: str = "https://api.groq.com/openai/v1"
    max_tool_budget: int = 8
    
    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRATOR_",
        env_file=".env",
        extra="ignore",
    )
