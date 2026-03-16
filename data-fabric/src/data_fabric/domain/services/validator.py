"""Domain service for validating market data quality."""

from __future__ import annotations

import statistics
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from data_fabric.domain.entities import MarketTick
from data_fabric.domain.errors import ValidationError


class DataValidator:
    """Rigorous validation for financial data points."""

    def validate_tick(self, tick: MarketTick) -> None:
        """Perform basic sanity checks on a single tick.
        
        Raises ValidationError if checks fail.
        """
        if tick.open <= 0 or tick.high <= 0 or tick.low <= 0 or tick.close <= 0:
            raise ValidationError("price", f"Negative or zero price detected for {tick.ticker}")
        
        if tick.volume < 0:
            raise ValidationError("volume", f"Negative volume detected for {tick.ticker}")
            
        if tick.high < tick.low:
            raise ValidationError("hilo", f"High price ({tick.high}) < Low price ({tick.low}) for {tick.ticker}")

    def detect_outliers(self, ticks: Sequence[MarketTick], z_threshold: float = 5.0) -> list[MarketTick]:
        """Detect price outliers using Z-score.
        
        Returns a list of ticks flagged as suspicious.
        """
        if len(ticks) < 3:
            return []

        closes = [float(t.close) for t in ticks]
        mean = statistics.mean(closes)
        stdev = statistics.stdev(closes) if len(closes) > 1 else 0

        if stdev == 0:
            return []

        flagged = []
        for tick in ticks:
            z_score = abs(float(tick.close) - mean) / stdev
            if z_score > z_threshold:
                flagged.append(tick)
        
        return flagged

    def detect_gaps(self, ticks: Sequence[MarketTick], expected_interval_seconds: int = 86400) -> list[datetime]:
        """Detect gaps in the timestamp sequence.
        
        Assumes ticks are sorted by timestamp.
        """
        if len(ticks) < 2:
            return []

        gaps = []
        for i in range(1, len(ticks)):
            diff = (ticks[i].timestamp - ticks[i-1].timestamp).total_seconds()
            if diff > expected_interval_seconds * 1.5:  # Allow for small drift
                gaps.append(ticks[i-1].timestamp)
        
        return gaps
