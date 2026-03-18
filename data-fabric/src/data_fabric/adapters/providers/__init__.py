"""Provider adapters used by background workers."""

from data_fabric.adapters.providers.market_intel import (
    CoinAPIMarketSource,
    GDELTEventSource,
    RedditSocialSource,
    RssFeedSource,
    UpstoxMarketSource,
    XSocialSource,
)
from data_fabric.adapters.providers.sec_edgar import SecEdgarSource
from data_fabric.adapters.sources import FREDMacroSource, PolygonMarketSource, WorldBankCountrySource

__all__ = [
    "CoinAPIMarketSource",
    "FREDMacroSource",
    "GDELTEventSource",
    "PolygonMarketSource",
    "RedditSocialSource",
    "RssFeedSource",
    "SecEdgarSource",
    "UpstoxMarketSource",
    "WorldBankCountrySource",
    "XSocialSource",
]
