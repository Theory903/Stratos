"""Real-data providers for India/crypto market intelligence."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    return str(value)


def _market_session(published_at: datetime | None = None) -> str:
    moment = (published_at or _utc_now()).astimezone(UTC)
    if moment.weekday() >= 5:
        return "closed"
    if 3 <= moment.hour < 10:
        return "india_cash"
    return "off_hours"


def _slug(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())[:48]


def _authority_for_provider(provider: str) -> str:
    mapping = {
        "rbi_rss": "A0",
        "sebi_rss": "A0",
        "nse_rss": "A0",
        "bse_rss": "A0",
        "gdelt": "A2",
        "reddit": "A3",
        "x": "A3",
    }
    return mapping.get(provider, "A2")


class UpstoxMarketSource:
    """Upstox V3 market-data adapter for India instruments."""

    def __init__(self, *, api_key: str, base_url: str = "https://api.upstox.com") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)

    @property
    def source_name(self) -> str:
        return "upstox"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def fetch(self, **params: object) -> list[dict[str, Any]]:
        if not self._api_key:
            return []
        tickers = params.get("tickers", [])
        if not isinstance(tickers, list):
            tickers = [tickers]

        bars: list[dict[str, Any]] = []
        for ticker in tickers:
            instrument = str(ticker)
            if "|" not in instrument:
                instrument = f"NSE_EQ|{instrument.upper()}"
            bars.extend(await self._fetch_daily_bars(instrument))
        return bars

    async def _fetch_daily_bars(self, instrument_key: str) -> list[dict[str, Any]]:
        end_date = _utc_now().date()
        start_date = end_date - timedelta(days=90)
        response = await self._client.get(
            f"{self._base_url}/v3/historical-candle/{quote_plus(instrument_key)}/day/{end_date.isoformat()}/{start_date.isoformat()}",
            headers=self._headers(),
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        candles = payload.get("candles", [])
        results: list[dict[str, Any]] = []
        for candle in candles:
            if len(candle) < 6:
                continue
            timestamp, open_price, high, low, close, volume = candle[:6]
            results.append(
                {
                    "ticker": instrument_key,
                    "asset_class": "equity",
                    "timestamp": _to_iso(timestamp),
                    "open": str(open_price),
                    "high": str(high),
                    "low": str(low),
                    "close": str(close),
                    "volume": int(volume or 0),
                }
            )
        return results

    async def fetch_order_book(self, instrument_key: str) -> dict[str, Any]:
        if not self._api_key:
            return {}
        response = await self._client.get(
            f"{self._base_url}/v3/market-quote/depth",
            params={"instrument_key": instrument_key},
            headers=self._headers(),
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        return payload.get(instrument_key, {})

    async def fetch_instrument_master(self, query: str) -> dict[str, Any]:
        if not self._api_key:
            return {}
        response = await self._client.get(
            f"{self._base_url}/v2/search/instruments",
            params={"query": query},
            headers=self._headers(),
        )
        response.raise_for_status()
        instruments = response.json().get("data", [])
        if not instruments:
            return {}
        instrument = instruments[0]
        return {
            "instrument_key": instrument.get("instrument_key") or instrument.get("instrumentKey"),
            "symbol": instrument.get("trading_symbol") or instrument.get("tradingSymbol") or query.upper(),
            "name": instrument.get("name") or query.upper(),
            "exchange": instrument.get("exchange") or "NSE",
            "asset_class": "equity",
            "source_url": f"{self._base_url}/v2/search/instruments?query={quote_plus(query)}",
        }

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            response = await self._client.get(f"{self._base_url}/v2/market/status", headers=self._headers())
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


class CoinAPIMarketSource:
    """CoinAPI market and order-book adapter."""

    def __init__(self, *, api_key: str, base_url: str = "https://rest.coinapi.io") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)

    @property
    def source_name(self) -> str:
        return "coinapi"

    def _headers(self) -> dict[str, str]:
        return {"X-CoinAPI-Key": self._api_key} if self._api_key else {}

    def _symbol(self, instrument: str) -> str:
        normalized = instrument.upper()
        if normalized.startswith("X:"):
            normalized = normalized.removeprefix("X:")
        if normalized.endswith("USD") and "_" not in normalized:
            return f"COINBASE_SPOT_{normalized[:-3]}_USD"
        return normalized.replace(":", "_")

    async def fetch(self, **params: object) -> list[dict[str, Any]]:
        if not self._api_key:
            return []
        tickers = params.get("tickers", [])
        if not isinstance(tickers, list):
            tickers = [tickers]
        bars: list[dict[str, Any]] = []
        for ticker in tickers:
            symbol_id = self._symbol(str(ticker))
            response = await self._client.get(
                f"{self._base_url}/v1/ohlcv/{symbol_id}/history",
                params={"period_id": "4HRS", "limit": 60},
                headers=self._headers(),
            )
            response.raise_for_status()
            for item in response.json():
                bars.append(
                    {
                        "ticker": str(ticker).upper(),
                        "asset_class": "crypto",
                        "timestamp": _to_iso(item.get("time_period_end") or item.get("time_close")),
                        "open": str(item.get("price_open", 0)),
                        "high": str(item.get("price_high", 0)),
                        "low": str(item.get("price_low", 0)),
                        "close": str(item.get("price_close", 0)),
                        "volume": int(float(item.get("volume_traded", 0) or 0)),
                    }
                )
        return bars

    async def fetch_order_book(self, instrument: str) -> dict[str, Any]:
        if not self._api_key:
            return {}
        symbol_id = self._symbol(instrument)
        response = await self._client.get(
            f"{self._base_url}/v1/orderbooks/{symbol_id}/current",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            response = await self._client.get(f"{self._base_url}/v1/exchanges", headers=self._headers())
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


class GDELTEventSource:
    """GDELT DOC API adapter for public news search."""

    def __init__(self, *, base_url: str = "https://api.gdeltproject.org/api/v2") -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)

    @property
    def source_name(self) -> str:
        return "gdelt"

    async def fetch(self, *, entity_id: str, limit: int = 25) -> list[dict[str, Any]]:
        response = await self._client.get(
            f"{self._base_url}/doc/doc",
            params={
                "query": entity_id,
                "mode": "artlist",
                "maxrecords": max(1, min(limit, 50)),
                "format": "json",
                "sort": "datedesc",
            },
        )
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])
        return [self._normalize_event(entity_id, article) for article in articles]

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(
                f"{self._base_url}/doc/doc",
                params={"query": "bitcoin", "mode": "artlist", "maxrecords": 1, "format": "json"},
            )
            return response.status_code == 200
        except Exception:
            return False

    def _normalize_event(self, entity_id: str, article: dict[str, Any]) -> dict[str, Any]:
        published = None
        if article.get("seendate"):
            published = datetime.strptime(str(article["seendate"]), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        headline = article.get("title") or article.get("url") or entity_id
        summary = article.get("socialimage") or article.get("domain") or headline
        event_id = f"gdelt:{_slug(entity_id)}:{_slug(headline)}"
        return {
            "event_id": event_id,
            "asset_scope": "cross_asset",
            "entity_ids": [entity_id.upper()],
            "headline": headline,
            "summary": summary,
            "body_ref": article.get("url"),
            "source_type": "news",
            "provider": self.source_name,
            "authority_grade": _authority_for_provider(self.source_name),
            "sentiment": 0.0,
            "relevance": 0.6,
            "novelty": 0.6,
            "market_session": _market_session(published),
            "dedupe_hash": event_id,
            "published_at": _to_iso(published or _utc_now()),
            "ingested_at": _to_iso(_utc_now()),
            "fresh_until": _to_iso((published or _utc_now()) + timedelta(hours=6)),
            "source_url": article.get("url"),
        }

    async def close(self) -> None:
        await self._client.aclose()


class RedditSocialSource:
    """Reddit search adapter for public social discussion."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        user_agent: str,
        base_url: str = "https://oauth.reddit.com",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = user_agent
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0, headers={"User-Agent": user_agent})
        self._token: str | None = None

    @property
    def source_name(self) -> str:
        return "reddit"

    async def _auth_header(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}", "User-Agent": self._user_agent}
        if not self._client_id or not self._client_secret:
            return {}
        basic = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode("utf-8")).decode("utf-8")
        response = await self._client.post(
            "https://www.reddit.com/api/v1/access_token",
            headers={"Authorization": f"Basic {basic}", "User-Agent": self._user_agent},
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()
        self._token = response.json().get("access_token")
        return {"Authorization": f"Bearer {self._token}", "User-Agent": self._user_agent}

    async def fetch(self, *, entity_id: str, limit: int = 25) -> list[dict[str, Any]]:
        headers = await self._auth_header()
        if not headers:
            return []
        response = await self._client.get(
            f"{self._base_url}/search",
            params={"q": entity_id, "sort": "new", "limit": max(1, min(limit, 50)), "type": "link"},
            headers=headers,
        )
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        return [self._normalize(entity_id, item.get("data", {})) for item in children]

    async def health_check(self) -> bool:
        if not self._client_id or not self._client_secret:
            return False
        try:
            headers = await self._auth_header()
            return bool(headers.get("Authorization"))
        except Exception:
            return False

    def _normalize(self, entity_id: str, post: dict[str, Any]) -> dict[str, Any]:
        published = datetime.fromtimestamp(float(post.get("created_utc", 0) or 0), tz=UTC)
        headline = post.get("title") or entity_id
        event_id = f"reddit:{post.get('id') or _slug(headline)}"
        sentiment = 0.25 if float(post.get("score", 0) or 0) > 0 else -0.1
        return {
            "event_id": event_id,
            "asset_scope": "cross_asset",
            "entity_ids": [entity_id.upper()],
            "headline": headline,
            "summary": post.get("selftext", "")[:400] or headline,
            "body_ref": f"https://reddit.com{post.get('permalink', '')}",
            "source_type": "social",
            "provider": self.source_name,
            "authority_grade": _authority_for_provider(self.source_name),
            "sentiment": sentiment,
            "relevance": 0.55,
            "novelty": 0.55,
            "market_session": _market_session(published),
            "dedupe_hash": event_id,
            "published_at": _to_iso(published),
            "ingested_at": _to_iso(_utc_now()),
            "fresh_until": _to_iso(published + timedelta(hours=4)),
            "source_url": f"https://reddit.com{post.get('permalink', '')}",
        }

    async def close(self) -> None:
        await self._client.aclose()


class XSocialSource:
    """X recent-search adapter."""

    def __init__(self, *, bearer_token: str, base_url: str = "https://api.x.com/2") -> None:
        self._bearer_token = bearer_token
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)

    @property
    def source_name(self) -> str:
        return "x"

    async def fetch(self, *, entity_id: str, limit: int = 25) -> list[dict[str, Any]]:
        if not self._bearer_token:
            return []
        response = await self._client.get(
            f"{self._base_url}/tweets/search/recent",
            params={"query": entity_id, "max_results": max(10, min(limit, 100)), "tweet.fields": "created_at,public_metrics"},
            headers={"Authorization": f"Bearer {self._bearer_token}"},
        )
        response.raise_for_status()
        tweets = response.json().get("data", [])
        return [self._normalize(entity_id, tweet) for tweet in tweets]

    async def health_check(self) -> bool:
        if not self._bearer_token:
            return False
        try:
            response = await self._client.get(
                f"{self._base_url}/tweets/search/recent",
                params={"query": "bitcoin", "max_results": 10},
                headers={"Authorization": f"Bearer {self._bearer_token}"},
            )
            return response.status_code == 200
        except Exception:
            return False

    def _normalize(self, entity_id: str, tweet: dict[str, Any]) -> dict[str, Any]:
        published = datetime.fromisoformat(str(tweet.get("created_at", _utc_now().isoformat())).replace("Z", "+00:00"))
        headline = str(tweet.get("text", entity_id)).strip()
        metrics = tweet.get("public_metrics", {})
        engagement = sum(float(metrics.get(key, 0) or 0) for key in ("retweet_count", "reply_count", "like_count", "quote_count"))
        sentiment = 0.2 if engagement > 10 else 0.0
        event_id = f"x:{tweet.get('id') or _slug(headline)}"
        return {
            "event_id": event_id,
            "asset_scope": "cross_asset",
            "entity_ids": [entity_id.upper()],
            "headline": headline[:200],
            "summary": headline[:500],
            "body_ref": f"https://x.com/i/web/status/{tweet.get('id')}",
            "source_type": "social",
            "provider": self.source_name,
            "authority_grade": _authority_for_provider(self.source_name),
            "sentiment": sentiment,
            "relevance": 0.58,
            "novelty": 0.6,
            "market_session": _market_session(published),
            "dedupe_hash": event_id,
            "published_at": _to_iso(published),
            "ingested_at": _to_iso(_utc_now()),
            "fresh_until": _to_iso(published + timedelta(hours=2)),
            "source_url": f"https://x.com/i/web/status/{tweet.get('id')}",
        }

    async def close(self) -> None:
        await self._client.aclose()


class RssFeedSource:
    """RSS feed adapter for policy and exchange announcements."""

    def __init__(self, *, name: str, feed_url: str, source_type: str) -> None:
        self._name = name
        self._feed_url = feed_url
        self._source_type = source_type
        self._client = httpx.AsyncClient(timeout=20.0)

    @property
    def source_name(self) -> str:
        return self._name

    async def fetch(self, *, entity_id: str, limit: int = 25) -> list[dict[str, Any]]:
        response = await self._client.get(self._feed_url)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        items = root.findall(".//item")
        events: list[dict[str, Any]] = []
        needle = entity_id.strip().lower()
        for item in items[: max(1, min(limit * 2, 100))]:
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date_raw = (item.findtext("pubDate") or "").strip()
            if needle and needle not in f"{title} {description}".lower():
                continue
            published = parsedate_to_datetime(pub_date_raw) if pub_date_raw else _utc_now()
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
            event_id = f"{self._name}:{_slug(title or description or entity_id)}"
            events.append(
                {
                    "event_id": event_id,
                    "asset_scope": "cross_asset",
                    "entity_ids": [entity_id.upper()] if entity_id else [],
                    "headline": title or entity_id.upper(),
                    "summary": description[:500] or title or entity_id.upper(),
                    "body_ref": link,
                    "source_type": self._source_type,
                    "provider": self._name,
                    "authority_grade": _authority_for_provider(self._name),
                    "sentiment": 0.0,
                    "relevance": 0.62,
                    "novelty": 0.65,
                    "market_session": _market_session(published),
                    "dedupe_hash": event_id,
                    "published_at": _to_iso(published),
                    "ingested_at": _to_iso(_utc_now()),
                    "fresh_until": _to_iso(published + timedelta(hours=6)),
                    "source_url": link or self._feed_url,
                }
            )
            if len(events) >= limit:
                break
        return events

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(self._feed_url)
            if response.status_code != 200:
                return False
            root = ElementTree.fromstring(response.text)
            return bool(root.findall(".//item"))
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


__all__ = [
    "CoinAPIMarketSource",
    "GDELTEventSource",
    "RedditSocialSource",
    "RssFeedSource",
    "UpstoxMarketSource",
    "XSocialSource",
]
