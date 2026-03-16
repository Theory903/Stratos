"""Insight builders that derive served snapshots from feature tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import pstdev
from typing import Any

from data_fabric.domain.entities import WorldState


@dataclass(slots=True)
class InsightBuilderUseCase:
    """Build served insight snapshots from feature tables."""

    store: Any
    documents: Any
    events: Any

    async def execute(self, message: dict[str, Any]) -> None:
        domain = str(message["domain"])
        entity_id = str(message["entity_id"])

        if domain == "world_state":
            observations = await self.store.get_latest_macro_series(
                ["DFF", "CPIAUCSL", "VIXCLS", "WALCL", "DCOILWTICO"]
            )
            state = self._build_world_state(observations)
            await self.store.save_world_state(
                state,
                feature_version="world-state-v1",
                provider_set=("fred",),
            )
            await self.documents.update_refresh_status("world_state", entity_id, "ready")
            await self.events.publish(
                topic="insight.build.completed",
                key=f"world_state:{entity_id}",
                payload={"domain": domain, "entity_id": entity_id},
            )
            return

        if domain == "market":
            bars = await self.store.get_market_ticks(entity_id.upper(), limit=30)
            if not bars:
                return
            closes = [float(bar.close) for bar in reversed(bars)]
            returns = [
                (current - previous) / previous
                for previous, current in zip(closes[:-1], closes[1:])
                if previous > 0
            ]
            volatility = pstdev(returns) if len(returns) >= 2 else 0.0
            momentum = returns[-1] if returns else 0.0
            label = "risk_on" if momentum >= 0 and volatility < 0.03 else "risk_off"
            await self.store.save_market_regime_snapshot(
                regime_label=label,
                confidence=max(0.1, min(0.99, 1.0 - min(volatility * 10, 0.8))),
                factor_summary={
                    "ticker": entity_id.upper(),
                    "momentum": momentum,
                    "volatility": volatility,
                },
                feature_version="market-regime-v1",
                provider_set=("massive",),
            )
            await self.documents.update_refresh_status("market", entity_id.upper(), "ready")
            await self.events.publish(
                topic="insight.build.completed",
                key=f"market:{entity_id}",
                payload={"domain": domain, "entity_id": entity_id.upper()},
            )

    def _build_world_state(self, grouped: dict[str, list[dict[str, Any]]]) -> WorldState:
        now = datetime.now(timezone.utc)
        latest_rate = self._latest_value(grouped, "DFF")
        latest_vix = self._latest_value(grouped, "VIXCLS")
        return WorldState(
            interest_rate=(latest_rate or 0.0) / 100.0,
            inflation=self._compute_year_over_year_change(grouped, "CPIAUCSL"),
            liquidity_index=self._normalize_latest_value(grouped, "WALCL"),
            geopolitical_risk=self._risk_proxy_from_vix(latest_vix),
            volatility_index=latest_vix or 0.0,
            commodity_index=self._normalize_latest_value(grouped, "DCOILWTICO"),
            timestamp=now,
            stored_at=now,
        )

    @staticmethod
    def _latest_value(grouped: dict[str, list[dict[str, Any]]], series_id: str) -> float | None:
        values = grouped.get(series_id, [])
        if not values:
            return None
        return float(values[0]["value"])

    @staticmethod
    def _compute_year_over_year_change(grouped: dict[str, list[dict[str, Any]]], series_id: str) -> float:
        values = grouped.get(series_id, [])
        if len(values) < 13:
            return 0.0
        latest = float(values[0]["value"])
        trailing_year = float(values[12]["value"])
        if trailing_year == 0:
            return 0.0
        return (latest / trailing_year) - 1.0

    @staticmethod
    def _normalize_latest_value(grouped: dict[str, list[dict[str, Any]]], series_id: str) -> float:
        values = [float(item["value"]) for item in grouped.get(series_id, [])]
        if not values:
            return 0.5
        latest = values[0]
        lower = min(values)
        upper = max(values)
        if upper == lower:
            return 0.5
        return max(0.0, min(1.0, (latest - lower) / (upper - lower)))

    @staticmethod
    def _risk_proxy_from_vix(latest_vix: float | None) -> float:
        if latest_vix is None:
            return 0.5
        return max(0.0, min(1.0, latest_vix / 40.0))
