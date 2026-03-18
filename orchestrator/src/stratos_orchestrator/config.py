"""Orchestrator configuration."""

import json
from pathlib import Path

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
    
    # External Data Source API Keys
    alpha_vantage_api_key: str | None = None
    finnhub_api_key: str | None = None
    newsapi_api_key: str | None = None
    coingecko_api_key: str | None = None
    polygon_api_key: str | None = None
    
    # External API Budget Controls (monthly cost limits in USD)
    # Set to 0 to disable a data source
    alpha_vantage_budget: float = 0.0
    finnhub_budget: float = 0.0
    newsapi_budget: float = 0.0
    coingecko_budget: float = 0.0
    polygon_budget: float = 0.0
    
    # External API Usage Tracking (reset monthly)
    alpha_vantage_calls_this_month: int = 0
    finnhub_calls_this_month: int = 0
    newsapi_calls_this_month: int = 0
    coingecko_calls_this_month: int = 0
    polygon_calls_this_month: int = 0
    
    # LLM Config
    llm_provider: str = "ollama"  # openai, anthropic, ollama, groq, nvidia
    ollama_model: str = "kimi-k2.5:cloud"
    ollama_base_url: str = "http://host.docker.internal:11434"
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
    runtime_persistence_dir: str = ".stratos/runtime"
    
    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRATOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    def is_data_source_enabled(self, source: str) -> bool:
        """Check if a data source is enabled based on budget and API key."""
        budget_map = {
            "alpha_vantage": self.alpha_vantage_budget,
            "finnhub": self.finnhub_budget,
            "newsapi": self.newsapi_budget,
            "coingecko": self.coingecko_budget,
            "polygon": self.polygon_budget,
        }
        api_key_map = {
            "alpha_vantage": self.alpha_vantage_api_key,
            "finnhub": self.finnhub_api_key,
            "newsapi": self.newsapi_api_key,
            "coingecko": self.coingecko_api_key,
            "polygon": self.polygon_api_key,
        }
        budget = budget_map.get(source, 0)
        api_key = api_key_map.get(source)
        return budget > 0 and api_key is not None
    
    def track_api_call(self, source: str) -> None:
        """Track an API call for budget management."""
        call_count_map = {
            "alpha_vantage": "alpha_vantage_calls_this_month",
            "finnhub": "finnhub_calls_this_month",
            "newsapi": "newsapi_calls_this_month",
            "coingecko": "coingecko_calls_this_month",
            "polygon": "polygon_calls_this_month",
        }
        attr = call_count_map.get(source)
        if attr:
            current = getattr(self, attr, 0)
            setattr(self, attr, current + 1)
    
    def get_api_usage(self, source: str) -> dict:
        """Get usage stats for a data source."""
        budget_map = {
            "alpha_vantage": (self.alpha_vantage_budget, self.alpha_vantage_calls_this_month),
            "finnhub": (self.finnhub_budget, self.finnhub_calls_this_month),
            "newsapi": (self.newsapi_budget, self.newsapi_calls_this_month),
            "coingecko": (self.coingecko_budget, self.coingecko_calls_this_month),
            "polygon": (self.polygon_budget, self.polygon_calls_this_month),
        }
        budget, calls = budget_map.get(source, (0.0, 0))
        return {
            "budget_usd": budget,
            "calls_this_month": calls,
            "enabled": self.is_data_source_enabled(source),
        }

    def mcp_server_config(self) -> dict[str, dict]:
        if not self.langchain_enable_mcp or not self.langchain_mcp_servers_json:
            return {}
        try:
            parsed = json.loads(self.langchain_mcp_servers_json)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @property
    def runtime_state_dir(self) -> Path:
        return Path(self.runtime_persistence_dir)
