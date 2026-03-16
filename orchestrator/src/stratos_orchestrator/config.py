"""Orchestrator configuration."""

import json

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
    qdrant_url: str = "http://localhost:6333"
    keycloak_url: str = "http://localhost:8080"
    
    # LLM Config
    llm_provider: str = "ollama"  # openai, anthropic, ollama, groq, nvidia
    ollama_model: str = "kimi-k2.5:cloud"
    openai_model: str = "gpt-4-turbo-preview"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_model: str = "moonshotai/kimi-k2-instruct-0905"
    groq_api_key: str | None = None
    groq_api_base: str = "https://api.groq.com/openai/v1"
    nvidia_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_api_key: str | None = None
    nvidia_temperature: float = 1.0
    nvidia_top_p: float = 0.95
    nvidia_max_tokens: int = 16384
    nvidia_reasoning_budget: int = 16384
    nvidia_enable_thinking: bool = True
    max_tool_budget: int = 8
    langchain_agent_model: str | None = None
    langchain_agent_max_tokens: int = 1024
    langchain_enable_mcp: bool = False
    langchain_mcp_servers_json: str | None = None
    
    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRATOR_",
        env_file=".env",
        extra="ignore",
    )

    def mcp_server_config(self) -> dict[str, dict]:
        if not self.langchain_enable_mcp or not self.langchain_mcp_servers_json:
            return {}
        try:
            parsed = json.loads(self.langchain_mcp_servers_json)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
