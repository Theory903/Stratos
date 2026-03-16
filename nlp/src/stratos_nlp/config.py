"""NLP service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NLP service settings."""
    
    port: int = 8004
    debug: bool = False
    
    # Model config
    finbert_model: str = "ProsusAI/finbert"
    spacy_model: str = "en_core_web_sm"
    sbert_model: str = "all-MiniLM-L6-v2"
    
    model_config = SettingsConfigDict(
        env_prefix="NLP_",
        env_file=".env",
        extra="ignore",
    )
