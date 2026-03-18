"""Service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Data Fabric configuration — loaded from env vars / .env file."""

    model_config = {"env_prefix": "DF_", "env_file": ".env"}

    # Database
    postgres_url: str = Field(
        default="postgresql+asyncpg://stratos:password@localhost:5432/stratos",
        validation_alias=AliasChoices("DF_POSTGRES_URL", "POSTGRES_URL"),
    )
    mongo_url: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices("DF_MONGO_URL", "MONGO_URL"),
    )
    mongo_database: str = Field(
        default="stratos",
        validation_alias=AliasChoices("DF_MONGO_DATABASE", "MONGO_DATABASE"),
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        validation_alias=AliasChoices("DF_REDIS_URL", "REDIS_URL"),
    )

    # Kafka
    kafka_brokers: str = Field(
        default="localhost:9092",
        validation_alias=AliasChoices("DF_KAFKA_BROKERS", "KAFKA_BROKERS"),
    )

    # Object Storage
    s3_endpoint: str = Field(
        default="http://localhost:9000",
        validation_alias=AliasChoices("DF_S3_ENDPOINT", "S3_ENDPOINT"),
    )
    s3_access_key: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices("DF_S3_ACCESS_KEY", "S3_ACCESS_KEY"),
    )
    s3_secret_key: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices("DF_S3_SECRET_KEY", "S3_SECRET_KEY"),
    )
    s3_bucket: str = Field(
        default="stratos-data",
        validation_alias=AliasChoices("DF_S3_BUCKET", "S3_BUCKET"),
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        validation_alias=AliasChoices("DF_QDRANT_URL", "QDRANT_URL"),
    )

    # External data sources
    polygon_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_POLYGON_API_KEY", "POLYGON_API_KEY"),
    )
    polygon_base_url: str = Field(
        default="https://api.polygon.io",
        validation_alias=AliasChoices(
            "DF_POLYGON_BASE_URL",
            "POLYGON_BASE_URL",
        ),
    )
    massive_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_MASSIVE_API_KEY", "MASSIVE_API_KEY"),
    )
    massive_base_url: str = Field(
        default="https://api.massive.com",
        validation_alias=AliasChoices(
            "DF_MASSIVE_BASE_URL",
            "MASSIVE_BASE_URL",
        ),
    )
    upstox_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_UPSTOX_API_KEY", "UPSTOX_API_KEY"),
    )
    upstox_base_url: str = Field(
        default="https://api.upstox.com",
        validation_alias=AliasChoices("DF_UPSTOX_BASE_URL", "UPSTOX_BASE_URL"),
    )
    coinapi_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_COINAPI_API_KEY", "COINAPI_API_KEY"),
    )
    coinapi_base_url: str = Field(
        default="https://rest.coinapi.io",
        validation_alias=AliasChoices("DF_COINAPI_BASE_URL", "COINAPI_BASE_URL"),
    )
    reddit_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("DF_REDDIT_CLIENT_ID", "REDDIT_CLIENT_ID"),
    )
    reddit_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("DF_REDDIT_CLIENT_SECRET", "REDDIT_CLIENT_SECRET"),
    )
    reddit_user_agent: str = Field(
        default="stratos-data-fabric/0.1",
        validation_alias=AliasChoices("DF_REDDIT_USER_AGENT", "REDDIT_USER_AGENT"),
    )
    x_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_X_API_KEY", "X_API_KEY"),
    )
    x_api_secret: str = Field(
        default="",
        validation_alias=AliasChoices("DF_X_API_SECRET", "X_API_SECRET"),
    )
    x_bearer_token: str = Field(
        default="",
        validation_alias=AliasChoices("DF_X_BEARER_TOKEN", "X_BEARER_TOKEN"),
    )
    x_base_url: str = Field(
        default="https://api.x.com/2",
        validation_alias=AliasChoices("DF_X_BASE_URL", "X_BASE_URL"),
    )
    gdelt_base_url: str = Field(
        default="https://api.gdeltproject.org/api/v2",
        validation_alias=AliasChoices("DF_GDELT_BASE_URL", "GDELT_BASE_URL"),
    )
    fred_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_FRED_API_KEY", "FRED_API_KEY"),
    )
    oanda_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DF_OANDA_API_KEY", "OANDA_API_KEY"),
    )
    world_bank_base_url: str = Field(
        default="https://api.worldbank.org/v2",
        validation_alias=AliasChoices("DF_WORLD_BANK_BASE_URL", "WORLD_BANK_BASE_URL"),
    )
    sec_base_url: str = Field(
        default="https://data.sec.gov",
        validation_alias=AliasChoices("DF_SEC_BASE_URL", "SEC_BASE_URL"),
    )
    sec_ticker_map_url: str = Field(
        default="https://www.sec.gov/files/company_tickers.json",
        validation_alias=AliasChoices("DF_SEC_TICKER_MAP_URL", "SEC_TICKER_MAP_URL"),
    )
    sec_user_agent: str = Field(
        default="STRATOS Research support@makeuslive.com",
        validation_alias=AliasChoices("DF_SEC_USER_AGENT", "SEC_USER_AGENT"),
    )
    rbi_rss_url: str = Field(
        default="https://www.rbi.org.in/Scripts/RSS.aspx?Id=4",
        validation_alias=AliasChoices("DF_RBI_RSS_URL", "RBI_RSS_URL"),
    )
    sebi_rss_url: str = Field(
        default="https://www.sebi.gov.in/sebirss.xml",
        validation_alias=AliasChoices("DF_SEBI_RSS_URL", "SEBI_RSS_URL"),
    )
    nse_rss_url: str = Field(
        default="https://www.nseindia.com/rss-feed",
        validation_alias=AliasChoices("DF_NSE_RSS_URL", "NSE_RSS_URL"),
    )
    bse_rss_url: str = Field(
        default="https://www.bseindia.com/rss-feed.xml",
        validation_alias=AliasChoices("DF_BSE_RSS_URL", "BSE_RSS_URL"),
    )

    # Service
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    tracked_companies: str = "AAPL"
    tracked_countries: str = "IND,USA"
    tracked_markets: str = "SPY,X:BTCUSD"

    @property
    def market_api_key(self) -> str:
        """Prefer the Massive key, but support legacy Polygon credentials."""
        return self.massive_api_key or self.polygon_api_key

    @property
    def market_base_url(self) -> str:
        """Select the matching API host for the configured market data provider."""
        if self.massive_api_key:
            return self.massive_base_url
        if self.polygon_api_key:
            return self.polygon_base_url
        return self.massive_base_url

    @property
    def tracked_company_list(self) -> list[str]:
        return [item.strip().upper() for item in self.tracked_companies.split(",") if item.strip()]

    @property
    def tracked_country_list(self) -> list[str]:
        return [item.strip().upper() for item in self.tracked_countries.split(",") if item.strip()]

    @property
    def tracked_market_list(self) -> list[str]:
        return [item.strip().upper() for item in self.tracked_markets.split(",") if item.strip()]
