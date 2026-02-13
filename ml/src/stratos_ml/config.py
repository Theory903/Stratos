"""ML service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "ML_", "env_file": ".env"}

    host: str = "0.0.0.0"
    port: int = 8003
    debug: bool = False
    model_registry_uri: str = "sqlite:///mlflow.db"
    feature_store_url: str = ""
