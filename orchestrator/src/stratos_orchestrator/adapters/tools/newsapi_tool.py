"""NewsAPI tool - news articles from NewsAPI.org."""

from __future__ import annotations

import httpx

from stratos_orchestrator.config import Settings
from stratos_orchestrator.adapters.tools.base import HttpTool


class NewsAPITool(HttpTool):
    """Get news articles from NewsAPI.org.
    
    Free tier: 100 requests/day for developer plan.
    API key required.
    """

    def __init__(self) -> None:
        settings = Settings()
        self._api_key = settings.newsapi_api_key
        self._settings = settings
        super().__init__("https://newsapi.org/v2")

    @property
    def name(self) -> str:
        return "newsapi"

    @property
    def description(self) -> str:
        return (
            "Get news articles from NewsAPI.org. "
            "Search by keyword, topic, or source. "
            "Requires API key (free tier: 100 requests/day)."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "top_headlines", "sources"],
                    "description": "What data to fetch.",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for search action).",
                },
                "q": {
                    "type": "string",
                    "description": "Keywords or phrases to search for.",
                },
                "category": {
                    "type": "string",
                    "description": "News category (business, entertainment, general, health, science, sports, technology).",
                    "default": "general",
                },
                "country": {
                    "type": "string",
                    "description": "Country code (us, gb, de, etc.).",
                    "default": "us",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of articles to return.",
                    "default": 10,
                },
                "language": {
                    "type": "string",
                    "description": "Language (en, de, fr, etc.).",
                    "default": "en",
                },
            },
            "required": ["action"],
        }

    async def execute(self, arguments: dict) -> dict:
        if not self._settings.is_data_source_enabled("newsapi"):
            return {"error": "NewsAPI is disabled. Set NEWSAPI_API_KEY and NEWSAPI_BUDGET > 0 to enable."}

        if not self._api_key:
            return {"error": "NewsAPI API key not configured. Set NEWSAPI_API_KEY in settings."}

        self._settings.track_api_call("newsapi")
        action = arguments.get("action", "search")
        limit = arguments.get("limit", 10)

        try:
            if action == "search":
                q = arguments.get("q") or arguments.get("query") or ""
                language = arguments.get("language", "en")
                params = {
                    "apiKey": self._api_key,
                    "q": q,
                    "language": language,
                    "pageSize": limit,
                    "sortBy": "publishedAt",
                }
                data = await self._request("GET", "/everything", params=params)
                articles = data.get("articles", [])
                return {
                    "action": "search",
                    "query": q,
                    "total_results": data.get("totalResults", 0),
                    "articles": [
                        {
                            "title": a.get("title"),
                            "description": a.get("description"),
                            "content": a.get("content"),
                            "url": a.get("url"),
                            "source": a.get("source", {}).get("name"),
                            "published_at": a.get("publishedAt"),
                            "author": a.get("author"),
                        }
                        for a in articles
                    ],
                }

            elif action == "top_headlines":
                category = arguments.get("category", "general")
                country = arguments.get("country", "us")
                params = {
                    "apiKey": self._api_key,
                    "category": category,
                    "country": country,
                    "pageSize": limit,
                }
                data = await self._request("GET", "/top-headlines", params=params)
                articles = data.get("articles", [])
                return {
                    "action": "top_headlines",
                    "category": category,
                    "country": country,
                    "total_results": data.get("totalResults", 0),
                    "articles": [
                        {
                            "title": a.get("title"),
                            "description": a.get("description"),
                            "url": a.get("url"),
                            "source": a.get("source", {}).get("name"),
                            "published_at": a.get("publishedAt"),
                            "author": a.get("author"),
                        }
                        for a in articles
                    ],
                }

            elif action == "sources":
                category = arguments.get("category", "general")
                language = arguments.get("language", "en")
                params = {
                    "apiKey": self._api_key,
                    "category": category,
                    "language": language,
                }
                data = await self._request("GET", "/sources", params=params)
                sources = data.get("sources", [])
                return {
                    "action": "sources",
                    "category": category,
                    "language": language,
                    "sources": [
                        {
                            "id": s.get("id"),
                            "name": s.get("name"),
                            "description": s.get("description"),
                            "url": s.get("url"),
                            "category": s.get("category"),
                            "language": s.get("language"),
                            "country": s.get("country"),
                        }
                        for s in sources
                    ],
                }

            else:
                return {"error": f"Unknown action: {action}"}

        except httpx.HTTPStatusError as e:
            return {"error": f"NewsAPI error: {e.response.status_code}", "detail": str(e)}
        except Exception as e:
            return {"error": str(e)}
