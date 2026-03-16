"""Fetch and compress webpage content into a tool-friendly snapshot."""

from __future__ import annotations

import html
import re

import httpx


_TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)[^>]*>.*?</\\1>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _extract_text(raw_html: str, max_chars: int) -> tuple[str, str]:
    title_match = _TITLE_PATTERN.search(raw_html)
    title = html.unescape(title_match.group(1)).strip() if title_match else ""
    cleaned = _SCRIPT_STYLE_PATTERN.sub(" ", raw_html)
    cleaned = _TAG_PATTERN.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
    return title, cleaned[:max_chars]


class WebpageReadTool:
    @property
    def name(self) -> str:
        return "webpage_read"

    @property
    def description(self) -> str:
        return (
            "Fetch a webpage and return a cleaned text extract with title. Use after search when the "
            "agent needs grounded details from a specific URL."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute URL to fetch."},
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum number of cleaned text characters to return.",
                    "default": 4000,
                },
            },
            "required": ["url"],
        }

    async def execute(self, arguments: dict) -> dict:
        url = str(arguments["url"]).strip()
        max_chars = max(500, min(int(arguments.get("max_chars", 4000)), 12000))

        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "STRATOS/1.0 (+https://localhost)"},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        title, excerpt = _extract_text(response.text, max_chars=max_chars)
        return {
            "url": str(response.url),
            "title": title,
            "content": excerpt,
        }
