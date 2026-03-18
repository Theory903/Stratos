"""Finance instrument resolution helpers."""

from __future__ import annotations

import re


_EXPLICIT_INSTRUMENT_PATTERN = re.compile(
    r"\b(?:X:[A-Z0-9]+|FX:[A-Z0-9]+|INDEX:[A-Z0-9]+|NSE_EQ\|[A-Z0-9]+|BSE_EQ\|[A-Z0-9]+|NSE:[A-Z0-9]+|BSE:[A-Z0-9]+)\b"
)
_ALIAS_MATCHERS: tuple[tuple[str, str], ...] = (
    ("bitcoin", "X:BTCUSD"),
    ("btc", "X:BTCUSD"),
    ("ethereum", "X:ETHUSD"),
    ("eth", "X:ETHUSD"),
    ("bank nifty", "INDEX:BANKNIFTY"),
    ("banknifty", "INDEX:BANKNIFTY"),
    ("nifty 50", "INDEX:NIFTY50"),
    ("nifty50", "INDEX:NIFTY50"),
    ("nifty", "INDEX:NIFTY50"),
    ("sensex", "INDEX:SENSEX"),
    ("india vix", "INDEX:INDIAVIX"),
    ("indiavix", "INDEX:INDIAVIX"),
)
_STOPWORDS = {
    "A",
    "ADD",
    "AGAINST",
    "AN",
    "AND",
    "AS",
    "AT",
    "BUY",
    "DO",
    "FOR",
    "HOW",
    "I",
    "IN",
    "IS",
    "LATEST",
    "LOOK",
    "MY",
    "NEWS",
    "OF",
    "ON",
    "OR",
    "OVER",
    "PORTFOLIO",
    "PRICE",
    "RESEARCH",
    "RISK",
    "SELL",
    "SHOULD",
    "THE",
    "THIS",
    "TODAY",
    "TRADE",
    "VS",
    "WATCH",
    "WHAT",
}


class InstrumentResolver:
    """Resolve a finance prompt to a canonical instrument identifier."""

    def resolve(self, query: str) -> str:
        explicit = self._explicit_instrument(query)
        if explicit:
            return explicit

        lowered = query.lower()
        for needle, instrument in _ALIAS_MATCHERS:
            if needle in lowered:
                return instrument

        fx_pair = self._fx_pair(query)
        if fx_pair:
            return fx_pair

        for token in re.findall(r"[A-Za-z:|0-9._-]+", query):
            cleaned = token.strip(".,!?()[]{}").upper()
            if not cleaned or cleaned in _STOPWORDS:
                continue
            if cleaned.startswith(("X:", "FX:", "INDEX:", "NSE_EQ|", "BSE_EQ|", "NSE:", "BSE:")):
                return cleaned
            if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
                return cleaned
            if cleaned.isalpha() and 2 <= len(cleaned) <= 12:
                return cleaned
        return "X:BTCUSD"

    @staticmethod
    def _explicit_instrument(query: str) -> str | None:
        match = _EXPLICIT_INSTRUMENT_PATTERN.search(query.upper())
        return match.group(0) if match else None

    @staticmethod
    def _fx_pair(query: str) -> str | None:
        lowered = query.lower()
        if "inr" in lowered and "usd" in lowered:
            return "FX:INRUSD"
        if "eur" in lowered and "usd" in lowered:
            return "FX:EURUSD"
        return None
