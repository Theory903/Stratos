"""General web search tool for current facts and documentation discovery."""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx


_RESULT_PATTERN = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_PATTERN = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    return html.unescape(_TAG_PATTERN.sub("", value)).strip()


def _normalize_href(href: str) -> str:
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        parsed = urlparse(href)
        if parsed.path == "/l/":
            uddg = parse_qs(parsed.query).get("uddg", [])
            if uddg:
                return unquote(uddg[0])
        return f"https://duckduckgo.com{href}"
    return href


class WebSearchTool:
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the public web for current facts, breaking news, vendor docs, pricing, and other "
            "time-sensitive information. Use this when the question depends on latest or external information."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "site": {
                    "type": "string",
                    "description": "Optional domain restriction such as docs.langchain.com or wikipedia.org.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of search results to return.",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict) -> dict:
        query = str(arguments["query"]).strip()
        site = str(arguments.get("site", "")).strip()
        limit = max(1, min(int(arguments.get("limit", 5)), 8))
        effective_query = f"site:{site} {query}" if site else query
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(effective_query)}"

        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "STRATOS/1.0 (+https://localhost)"},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        results = []
        for match in _RESULT_PATTERN.finditer(response.text):
            title = _strip_html(match.group("title"))
            href = _normalize_href(html.unescape(match.group("href")))
            if not title or not href:
                continue
            results.append({"title": title, "url": href})
            if len(results) >= limit:
                break

        return {
            "query": query,
            "site": site or None,
            "results": results,
        }
