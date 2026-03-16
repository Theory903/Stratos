"""Logging helpers that work with or without structlog installed."""

from __future__ import annotations

import logging
from typing import Any


class _KeywordLoggerAdapter:
    """Allow structlog-style keyword fields with stdlib logging."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _format(self, event: str, **fields: Any) -> str:
        if not fields:
            return event
        context = " ".join(f"{key}={value!r}" for key, value in sorted(fields.items()))
        return f"{event} {context}"

    def info(self, event: str, **fields: Any) -> None:
        self._logger.info(self._format(event, **fields))

    def warning(self, event: str, **fields: Any) -> None:
        self._logger.warning(self._format(event, **fields))

    def error(self, event: str, **fields: Any) -> None:
        self._logger.error(self._format(event, **fields))

    def critical(self, event: str, **fields: Any) -> None:
        self._logger.critical(self._format(event, **fields))


def get_logger(name: str):
    try:  # pragma: no cover
        import structlog

        return structlog.get_logger()
    except ImportError:  # pragma: no cover
        return _KeywordLoggerAdapter(logging.getLogger(name))
