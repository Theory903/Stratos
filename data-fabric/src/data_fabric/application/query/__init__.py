"""Snapshot-only and internal-compute query use cases."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any

from data_fabric.application.common import FreshnessPolicy, SnapshotMeta, SnapshotRead


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _percentile_rank(current: float, values: list[float]) -> float:
    if not values:
        return 0.0
    count = sum(1 for value in values if value <= current)
    return count / len(values)


@dataclass(slots=True)
class QueryCompanyUseCase:
    store: Any
    refreshes: Any

    async def execute(self, ticker: str) -> SnapshotRead[Any]:
        normalized = ticker.upper()
        snapshot = await self.store.get_company_snapshot(normalized)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="company",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCountryUseCase:
    store: Any
    refreshes: Any

    async def execute(self, country_code: str) -> SnapshotRead[Any]:
        normalized = country_code.upper()
        snapshot = await self.store.get_country_snapshot(normalized)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="country",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryWorldStateUseCase:
    store: Any
    refreshes: Any

    async def execute(self) -> SnapshotRead[Any]:
        snapshot = await self.store.get_world_state_snapshot()
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="world_state",
            entity_id="global",
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryMarketHistoryUseCase:
    store: Any
    refreshes: Any

    async def execute(self, ticker: str, *, limit: int = 100) -> SnapshotRead[list[Any]]:
        normalized = ticker.upper()
        snapshot = await self.store.get_market_snapshot(normalized, limit=limit)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="market",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryMarketRegimeUseCase:
    store: Any
    refreshes: Any

    async def execute(self) -> SnapshotRead[dict[str, Any]]:
        snapshot = await self.store.get_market_regime_snapshot()
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="market_regime",
            entity_id="global",
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCompanyFilingsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, ticker: str) -> SnapshotRead[list[dict[str, Any]]]:
        normalized = ticker.upper()
        record = await self.documents.get_company_filings(normalized)
        return await _collection_response(
            record=record,
            entity_type="company_filings",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCompanyNewsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, ticker: str) -> SnapshotRead[list[dict[str, Any]]]:
        normalized = ticker.upper()
        record = await self.documents.get_company_news_snapshot(normalized)
        if record is None:
            record = await self.documents.get_normalized_news(normalized)
        return await _collection_response(
            record=record,
            entity_type="news",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QuerySocialFeedUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, entity: str) -> SnapshotRead[list[dict[str, Any]]]:
        normalized = entity.upper()
        record = await self.documents.get_normalized_event_stream("social", normalized)
        return await _collection_response(
            record=record,
            entity_type="social",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryExchangeAnnouncementsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, entity: str) -> SnapshotRead[list[dict[str, Any]]]:
        normalized = entity.upper()
        record = await self.documents.get_normalized_event_stream("exchange_announcements", normalized)
        return await _collection_response(
            record=record,
            entity_type="announcements",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryOrderBookUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, instrument: str) -> SnapshotRead[dict[str, Any]]:
        normalized = instrument.upper()
        snapshot = await self.documents.get_order_book_snapshot(normalized)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="orderbook",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryPolicyEventsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.get_policy_documents(normalized)
        return await _collection_response(
            record=record,
            entity_type="policy",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class SearchPolicyUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, query: str, *, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.search_policy_documents(normalized, query)
        return await _collection_response(
            record=record,
            entity_type="policy",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryEventsFeedUseCase:
    store: Any
    documents: Any
    refreshes: Any

    async def execute(self, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.get_event_feed(normalized)
        if record is None:
            await _ensure_event_views(normalized, self.store, self.documents)
            record = await self.documents.get_event_feed(normalized)
        return await _collection_response(
            record=record,
            entity_type="events_feed",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class SearchEventsUseCase:
    store: Any
    documents: Any
    refreshes: Any

    async def execute(self, query: str, *, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.search_event_feed(normalized, query)
        if record is None:
            await _ensure_event_views(normalized, self.store, self.documents)
            record = await self.documents.search_event_feed(normalized, query)
        return await _collection_response(
            record=record,
            entity_type="events_feed",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryEventClustersUseCase:
    store: Any
    documents: Any
    refreshes: Any

    async def execute(self, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.get_event_clusters(normalized)
        if record is None:
            await _ensure_event_views(normalized, self.store, self.documents)
            record = await self.documents.get_event_clusters(normalized)
        return await _collection_response(
            record=record,
            entity_type="events_clusters",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryEventPulseUseCase:
    store: Any
    documents: Any
    refreshes: Any

    async def execute(self, scope: str) -> SnapshotRead[dict[str, Any]]:
        normalized = scope.lower()
        snapshot = await self.documents.get_event_pulse(normalized)
        if snapshot is None:
            await _ensure_event_views(normalized, self.store, self.documents)
            snapshot = await self.documents.get_event_pulse(normalized)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="events_pulse",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCompareMetricUseCase:
    store: Any
    refreshes: Any

    async def execute(
        self,
        *,
        entity_type: str,
        metric: str,
        entity_id: str = "global",
        limit: int = 24,
    ) -> SnapshotRead[dict[str, Any]]:
        normalized_type = entity_type.lower()
        normalized_id = entity_id.upper() if normalized_type in {"company", "country", "market"} else entity_id.lower()
        values = await _load_metric_series(self.store, normalized_type, metric, normalized_id, limit)
        if not values:
            return await _snapshot_response(None, "compare_metric", f"{normalized_type}:{normalized_id}:{metric}", self.refreshes)

        current = values[0]
        average = mean(values)
        volatility = pstdev(values) if len(values) >= 2 else 0.0
        z_score = 0.0 if volatility == 0 else (current - average) / volatility
        return SnapshotRead(
            status="ready",
            data={
                "entity_type": normalized_type,
                "entity_id": normalized_id,
                "metric": metric,
                "current": current,
                "average": average,
                "minimum": min(values),
                "maximum": max(values),
                "percentile_rank": _percentile_rank(current, values),
                "z_score": z_score,
                "series": list(reversed(values)),
            },
            meta=SnapshotMeta(
                entity_type="compare_metric",
                entity_id=f"{normalized_type}:{normalized_id}:{metric}",
                as_of=None,
                computed_at=None,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="compare-v1",
                provider_set=("internal",),
            ),
        )


@dataclass(slots=True)
class QueryCompareEntityUseCase:
    store: Any
    refreshes: Any

    async def execute(self, *, entity_type: str, entity_id: str) -> SnapshotRead[dict[str, Any]]:
        normalized_type = entity_type.lower()
        normalized_id = entity_id.upper() if normalized_type in {"company", "country"} else entity_id.lower()

        if normalized_type == "company":
            snapshots = await self.store.list_company_snapshots(normalized_id, limit=2)
            keys = (
                "earnings_quality",
                "leverage_ratio",
                "free_cash_flow_stability",
                "fraud_score",
                "moat_score",
            )
        elif normalized_type == "country":
            snapshots = await self.store.list_country_snapshots(normalized_id, limit=2)
            keys = (
                "debt_gdp",
                "fx_reserves",
                "fiscal_deficit",
                "political_stability",
                "currency_volatility",
            )
        else:
            return await _snapshot_response(None, "compare_entity", f"{normalized_type}:{normalized_id}", self.refreshes)

        if not snapshots:
            return await _snapshot_response(None, "compare_entity", f"{normalized_type}:{normalized_id}", self.refreshes)

        current = snapshots[0].data
        previous = snapshots[1].data if len(snapshots) > 1 else None
        deltas = {
            key: (_safe_float(getattr(current, key)) - _safe_float(getattr(previous, key)))
            if previous is not None
            else 0.0
            for key in keys
        }
        return SnapshotRead(
            status="ready",
            data={
                "entity_type": normalized_type,
                "entity_id": normalized_id,
                "current": {key: getattr(current, key) for key in keys},
                "previous": {key: getattr(previous, key) for key in keys} if previous is not None else None,
                "deltas": deltas,
            },
            meta=SnapshotMeta(
                entity_type="compare_entity",
                entity_id=f"{normalized_type}:{normalized_id}",
                as_of=snapshots[0].as_of,
                computed_at=snapshots[0].computed_at,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="compare-v1",
                provider_set=snapshots[0].provider_set,
            ),
        )


@dataclass(slots=True)
class QuerySimilarRegimesUseCase:
    store: Any
    refreshes: Any

    async def execute(self, limit: int = 6) -> SnapshotRead[dict[str, Any]]:
        snapshots = await self.store.list_market_regime_snapshots(limit=max(limit + 1, 8))
        if not snapshots:
            return await _snapshot_response(None, "history_regimes", "global", self.refreshes)

        current = snapshots[0].data
        analogs: list[dict[str, Any]] = []
        for snapshot in snapshots[1:]:
            score = 1.0 - abs(_safe_float(snapshot.data.get("confidence")) - _safe_float(current.get("confidence")))
            analogs.append(
                {
                    "regime_label": snapshot.data.get("regime_label"),
                    "confidence": snapshot.data.get("confidence"),
                    "similarity": max(0.0, min(1.0, score)),
                    "as_of": snapshot.as_of.isoformat(),
                    "factor_summary": snapshot.data.get("factor_summary", {}),
                }
            )
        analogs.sort(key=lambda item: item["similarity"], reverse=True)
        return SnapshotRead(
            status="ready",
            data={
                "current": current,
                "analogs": analogs[:limit],
            },
            meta=SnapshotMeta(
                entity_type="history_regimes",
                entity_id="global",
                as_of=snapshots[0].as_of,
                computed_at=snapshots[0].computed_at,
                freshness=FreshnessPolicy.classify("market_regime", snapshots[0].as_of),
                refresh_enqueued=False,
                feature_version="history-v1",
                provider_set=snapshots[0].provider_set,
            ),
        )


@dataclass(slots=True)
class QueryAnomalyUseCase:
    store: Any
    refreshes: Any

    async def execute(
        self,
        *,
        entity: str,
        entity_type: str = "market",
        metric: str | None = None,
    ) -> SnapshotRead[dict[str, Any]]:
        normalized_type = entity_type.lower()
        default_metric = {
            "market": "close",
            "company": "fraud_score",
            "country": "currency_volatility",
            "world_state": "inflation",
        }.get(normalized_type, "close")
        selected_metric = metric or default_metric
        compared = await QueryCompareMetricUseCase(store=self.store, refreshes=self.refreshes).execute(
            entity_type=normalized_type,
            entity_id=entity,
            metric=selected_metric,
        )
        if compared.status != "ready" or compared.data is None:
            return compared
        z_score = _safe_float(compared.data.get("z_score"))
        severity = "high" if abs(z_score) >= 2 else "medium" if abs(z_score) >= 1 else "low"
        explanation = (
            f"{entity.upper()} shows a {severity} anomaly on {selected_metric} "
            f"with z-score {z_score:.2f} versus its recent internal history."
        )
        anomaly_data = dict(compared.data)
        anomaly_data["severity"] = severity
        anomaly_data["explanation"] = explanation
        return SnapshotRead(
            status="ready",
            data=anomaly_data,
            meta=SnapshotMeta(
                entity_type="anomaly",
                entity_id=f"{normalized_type}:{entity.lower()}:{selected_metric}",
                as_of=compared.meta.as_of,
                computed_at=compared.meta.computed_at,
                freshness=compared.meta.freshness,
                refresh_enqueued=compared.meta.refresh_enqueued,
                feature_version=compared.meta.feature_version,
                provider_set=compared.meta.provider_set,
            ),
        )


@dataclass(slots=True)
class QueryPortfolioUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, name: str = "primary") -> SnapshotRead[dict[str, Any]]:
        snapshot = await self.documents.get_portfolio_snapshot(name)
        if snapshot is None:
            return _manual_pending("portfolio", name)
        return await _snapshot_response(snapshot, "portfolio", name, self.refreshes)


@dataclass(slots=True)
class UpsertPortfolioUseCase:
    documents: Any

    async def execute(
        self,
        *,
        name: str,
        benchmark: str,
        positions: list[dict[str, Any]],
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot = {
            "name": name,
            "benchmark": benchmark,
            "positions": positions,
            "constraints": constraints or {},
        }
        await self.documents.save_portfolio_snapshot(name=name, data=snapshot)
        await self.documents.append_portfolio_decision(
            name=name,
            decision={
                "action": "positions_updated",
                "benchmark": benchmark,
                "position_count": len(positions),
            },
        )
        return snapshot


@dataclass(slots=True)
class QueryPortfolioExposureUseCase:
    documents: Any
    store: Any
    refreshes: Any

    async def execute(self, name: str = "primary") -> SnapshotRead[dict[str, Any]]:
        portfolio = await self.documents.get_portfolio_snapshot(name)
        if portfolio is None:
            return _manual_pending("portfolio_exposures", name)
        data = await _compute_portfolio_metrics(self.store, portfolio.data)
        return SnapshotRead(
            status="ready",
            data={
                "name": name,
                "total_market_value": data["total_market_value"],
                "asset_class_exposure": data["asset_class_exposure"],
                "top_positions": data["positions"],
            },
            meta=SnapshotMeta(
                entity_type="portfolio_exposures",
                entity_id=name,
                as_of=portfolio.as_of,
                computed_at=portfolio.computed_at,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="portfolio-v1",
                provider_set=portfolio.provider_set,
            ),
        )


@dataclass(slots=True)
class QueryPortfolioRiskUseCase:
    documents: Any
    store: Any
    refreshes: Any

    async def execute(self, name: str = "primary") -> SnapshotRead[dict[str, Any]]:
        portfolio = await self.documents.get_portfolio_snapshot(name)
        regime = await self.store.get_market_regime_snapshot()
        world = await self.store.get_world_state_snapshot()
        if portfolio is None:
            return _manual_pending("portfolio_risk", name)

        metrics = await _compute_portfolio_metrics(self.store, portfolio.data)
        max_weight = max((item["weight"] for item in metrics["positions"]), default=0.0)
        concentration = max_weight
        vol = metrics["estimated_daily_volatility"]
        var_95 = metrics["value_at_risk_95"]
        flags: list[str] = []
        if concentration > 0.55:
            flags.append("Portfolio is concentrated in a single position.")
        if world and world.data.inflation > 0.03:
            flags.append("Sticky inflation is a portfolio-level macro headwind.")
        if regime and regime.data.get("regime_label") == "risk_off":
            flags.append("Current regime favors lower beta and tighter position sizing.")

        return SnapshotRead(
            status="ready",
            data={
                "name": name,
                "estimated_daily_volatility": vol,
                "value_at_risk_95": var_95,
                "concentration_risk": concentration,
                "regime": regime.data if regime else None,
                "risk_flags": flags,
            },
            meta=SnapshotMeta(
                entity_type="portfolio_risk",
                entity_id=name,
                as_of=portfolio.as_of,
                computed_at=portfolio.computed_at,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="portfolio-risk-v1",
                provider_set=("internal",),
            ),
        )


@dataclass(slots=True)
class RunPortfolioScenarioUseCase:
    documents: Any
    store: Any

    async def execute(self, *, name: str, scenario: str) -> dict[str, Any] | None:
        portfolio = await self.documents.get_portfolio_snapshot(name)
        if portfolio is None:
            return None

        multipliers = {
            "oil_sticky_india_btc": {"equity": -0.06, "crypto": 0.09, "commodity": 0.04},
            "risk_off": {"equity": -0.08, "crypto": -0.14, "commodity": 0.02},
            "india_capex_boom": {"equity": 0.05, "crypto": 0.03, "commodity": 0.01},
        }.get(scenario, {"equity": -0.02, "crypto": -0.03, "commodity": 0.0})

        metrics = await _compute_portfolio_metrics(self.store, portfolio.data)
        impacted_positions = []
        total_impact = 0.0
        for item in metrics["positions"]:
            shock = multipliers.get(item["asset_class"], -0.01)
            pnl_impact = item["market_value"] * shock
            total_impact += pnl_impact
            impacted_positions.append(
                {
                    "ticker": item["ticker"],
                    "asset_class": item["asset_class"],
                    "shock": shock,
                    "estimated_pnl_impact": pnl_impact,
                }
            )

        result = {
            "scenario": scenario,
            "portfolio_name": name,
            "estimated_total_pnl_impact": total_impact,
            "positions": impacted_positions,
        }
        await self.documents.append_portfolio_decision(
            name=name,
            decision={
                "action": "scenario_run",
                "scenario": scenario,
                "estimated_total_pnl_impact": total_impact,
            },
        )
        return result


@dataclass(slots=True)
class RunPortfolioRebalanceUseCase:
    documents: Any
    store: Any

    async def execute(self, *, name: str = "primary") -> dict[str, Any] | None:
        portfolio = await self.documents.get_portfolio_snapshot(name)
        if portfolio is None:
            return None

        metrics = await _compute_portfolio_metrics(self.store, portfolio.data)
        suggested: list[dict[str, Any]] = []
        current_positions = metrics["positions"]
        capped_weight = 0.6
        for item in current_positions:
            target_weight = min(item["weight"], capped_weight)
            if item["asset_class"] == "crypto":
                target_weight = min(target_weight, 0.35)
            suggested.append(
                {
                    "ticker": item["ticker"],
                    "current_weight": item["weight"],
                    "target_weight": target_weight,
                    "action": "trim" if target_weight < item["weight"] else "hold",
                }
            )

        result = {
            "portfolio_name": name,
            "suggestions": suggested,
            "rationale": "Trim concentration and cap crypto risk while retaining core exposure.",
        }
        await self.documents.append_portfolio_decision(
            name=name,
            decision={
                "action": "rebalance_suggested",
                "suggestions": suggested,
            },
        )
        return result


@dataclass(slots=True)
class QueryPortfolioDecisionLogUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, name: str = "primary") -> SnapshotRead[list[dict[str, Any]]]:
        record = await self.documents.get_portfolio_decision_log(name)
        if record is None:
            return _manual_pending("portfolio_decision_log", name)
        return await _collection_response(record, "portfolio_decision_log", name, self.refreshes)


@dataclass(slots=True)
class QueryDecisionQueueUseCase:
    documents: Any
    store: Any
    refreshes: Any

    async def execute(self, name: str = "primary") -> SnapshotRead[dict[str, Any]]:
        portfolio = await self.documents.get_portfolio_snapshot(name)
        world = await self.store.get_world_state_snapshot()
        regime = await self.store.get_market_regime_snapshot()
        feed = await self.documents.get_event_feed("global")
        if feed is None:
            await _ensure_event_views("global", self.store, self.documents)
            feed = await self.documents.get_event_feed("global")
        if portfolio is None or world is None or regime is None or feed is None:
            return _manual_pending("decision_queue", name)

        metrics = await _compute_portfolio_metrics(self.store, portfolio.data)
        top_position = metrics["positions"][0]["ticker"] if metrics["positions"] else "N/A"
        top_risks = [
            {"title": "Sticky inflation", "why": f"CPI is running at {world.data.inflation * 100:.2f}%."},
            {"title": "Portfolio concentration", "why": f"Largest holding is {top_position}."},
        ]
        top_opportunities = [
            {"title": "BTC relative strength", "why": "Crypto sleeve remains a catalyst when risk appetite improves."},
            {"title": "India policy support", "why": "India sovereign backdrop remains supportive for selective cyclicals."},
        ]
        actions = [
            "Run the oil_sticky_india_btc scenario against the current book.",
            "Trim oversized single-name weights before adding new risk.",
            "Use the agent to synthesize the queue into a PM decision memo.",
        ]
        return SnapshotRead(
            status="ready",
            data={
                "portfolio_name": name,
                "top_risks": top_risks,
                "top_opportunities": top_opportunities,
                "watchlist_changes": [item["title"] for item in list(feed.items)[:3]],
                "recommended_actions": actions,
                "regime": regime.data,
            },
            meta=SnapshotMeta(
                entity_type="decision_queue",
                entity_id=name,
                as_of=portfolio.as_of,
                computed_at=portfolio.computed_at,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="decision-queue-v1",
                provider_set=("internal",),
            ),
        )


@dataclass(slots=True)
class QueryProviderHealthUseCase:
    providers: dict[str, Any]
    settings: Any

    async def execute(self) -> SnapshotRead[dict[str, Any]]:
        from datetime import UTC, datetime

        checks = await asyncio.gather(
            *(self._check_provider(name, provider) for name, provider in self.providers.items())
        )
        healthy = sum(1 for item in checks if item["status"] == "healthy")
        degraded = sum(1 for item in checks if item["status"] == "degraded")
        unavailable = sum(1 for item in checks if item["status"] == "unavailable")
        overall_status = "healthy" if degraded == 0 and unavailable == 0 else "degraded" if healthy > 0 else "down"
        return SnapshotRead(
            status="ready",
            data={
                "overall_status": overall_status,
                "summary": (
                    f"{healthy} healthy, {degraded} degraded, {unavailable} unavailable providers across market, event, and policy coverage."
                ),
                "checked_at": datetime.now(UTC).isoformat(),
                "providers": checks,
                "notes": [
                    "Health checks are live reachability checks where provider adapters support them.",
                    "Unavailable means credentials or feed configuration are missing in this environment.",
                ],
                "overview": {
                    "total": len(checks),
                    "healthy": healthy,
                    "degraded": degraded,
                    "unavailable": unavailable,
                    "coverage_ratio": healthy / len(checks) if checks else 0.0,
                },
                "primary_markets": {
                    "india_equities": "upstox",
                    "crypto": "coinapi",
                    "fallback_market": "massive",
                    "macro": "fred",
                },
            },
            meta=SnapshotMeta(
                entity_type="providers_health",
                entity_id="global",
                as_of=None,
                computed_at=None,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="provider-health-v1",
                provider_set=("internal",),
            ),
        )

    async def _check_provider(self, name: str, provider: Any) -> dict[str, Any]:
        configured = _provider_is_configured(name, self.settings)
        health_check = getattr(provider, "health_check", None)
        healthy = False
        if configured and callable(health_check):
            healthy = bool(await health_check())
        status = "healthy" if configured and healthy else "degraded" if configured else "unavailable"
        return {
            "provider": name,
            "configured": configured,
            "healthy": healthy,
            "status": status,
            "freshness": "fresh" if healthy else "stale" if configured else None,
            "lag_seconds": None,
            "detail": f"{_provider_coverage(name).replace('_', ' ')} coverage",
            "source_name": getattr(provider, "source_name", name),
            "source_coverage": 1.0 if configured else 0.0,
        }


@dataclass(slots=True)
class QueryDecisionContextUseCase:
    documents: Any
    store: Any
    refreshes: Any

    async def execute(self, instrument: str, *, portfolio_name: str = "primary") -> SnapshotRead[dict[str, Any]]:
        normalized = instrument.upper()
        portfolio = await self.documents.get_portfolio_snapshot(portfolio_name)
        market = await self.store.get_market_snapshot(normalized, limit=20)
        order_book = await self.documents.get_order_book_snapshot(normalized)
        news = await self.documents.get_normalized_event_stream("company_news", normalized)
        social = await self.documents.get_normalized_event_stream("social", normalized)
        announcements = await self.documents.get_normalized_event_stream("exchange_announcements", normalized)
        policy = await self.documents.get_policy_documents("india")

        if portfolio is None or market is None:
            return _manual_pending("decision_context", normalized)

        risk = await QueryPortfolioRiskUseCase(
            documents=self.documents,
            store=self.store,
            refreshes=self.refreshes,
        ).execute(portfolio_name)
        exposures = await QueryPortfolioExposureUseCase(
            documents=self.documents,
            store=self.store,
            refreshes=self.refreshes,
        ).execute(portfolio_name)
        data = {
            "instrument": normalized,
            "portfolio_name": portfolio_name,
            "market": [*_serialize_ticks(market.data)],
            "order_book": order_book.data if order_book else None,
            "news": list(news.items) if news else [],
            "social": list(social.items) if social else [],
            "exchange_announcements": list(announcements.items) if announcements else [],
            "policy": list(policy.items) if policy else [],
            "portfolio": portfolio.data,
            "portfolio_exposures": exposures.data if exposures.status == "ready" else None,
            "portfolio_risk": risk.data if risk.status == "ready" else None,
        }
        return SnapshotRead(
            status="ready",
            data=data,
            meta=SnapshotMeta(
                entity_type="decision_context",
                entity_id=normalized,
                as_of=market.as_of,
                computed_at=market.computed_at,
                freshness=FreshnessPolicy.classify("decision_context", market.as_of),
                refresh_enqueued=False,
                feature_version="decision-context-v1",
                provider_set=tuple(
                    sorted(
                        {
                            *market.provider_set,
                            *(order_book.provider_set if order_book else ()),
                            *(news.provider_set if news else ()),
                            *(social.provider_set if social else ()),
                            *(announcements.provider_set if announcements else ()),
                        }
                    )
                ),
            ),
        )


@dataclass(slots=True)
class ReplayDecisionUseCase:
    documents: Any
    store: Any
    refreshes: Any

    async def execute(self, instrument: str, *, as_of: Any, portfolio_name: str = "primary") -> SnapshotRead[dict[str, Any]]:
        normalized = instrument.upper()
        replay_as_of = _parse_as_of(as_of)
        market = await self.store.get_market_snapshot(normalized, limit=60, as_of=replay_as_of)
        portfolio = await self.documents.get_portfolio_snapshot(portfolio_name)
        if market is None or portfolio is None:
            return _manual_pending("replay_decision", normalized)

        news = await self.documents.get_normalized_news(normalized, as_of=replay_as_of)
        social = await self.documents.get_social_posts(normalized, as_of=replay_as_of)
        announcements = await self.documents.get_exchange_announcements(normalized, as_of=replay_as_of)
        order_book = await self.documents.get_order_book_snapshot(normalized, as_of=replay_as_of)
        policy = await self.documents.get_policy_documents_as_of("india", as_of=replay_as_of)
        risk = await QueryPortfolioRiskUseCase(
            documents=self.documents,
            store=self.store,
            refreshes=self.refreshes,
        ).execute(portfolio_name)
        exposures = await QueryPortfolioExposureUseCase(
            documents=self.documents,
            store=self.store,
            refreshes=self.refreshes,
        ).execute(portfolio_name)
        closes = [float(item.close) for item in market.data[:20]]
        asset_class = market.data[0].asset_class.value if market.data else "equity"
        move = 0.0
        if len(closes) >= 2 and closes[-1] != 0:
            move = (closes[0] - closes[-1]) / closes[-1]
        score_breakdown = _build_replay_score_breakdown(
            asset_class=asset_class,
            historical_move=move,
            news_count=len(news.items) if news else 0,
            social_count=len(social.items) if social else 0,
            policy_count=len(policy.items) if policy else 0,
            has_order_book=order_book is not None,
        )
        score = score_breakdown["score"]
        stance = "BUY" if score >= 0.63 else "SELL" if score <= 0.37 else "HOLD"
        veto_reasons = _replay_veto_reasons(
            asset_class=asset_class,
            stance=stance,
            score=score,
            has_order_book=order_book is not None,
            portfolio_risk=risk.data if risk.status == "ready" else None,
        )
        allowed = len(veto_reasons) == 0
        final_action = stance if allowed else "NO_TRADE"
        confidence = abs(score - 0.5) * 2
        position_size_pct = min(0.06, max(0.0, confidence * (0.02 if asset_class == "crypto" else 0.03)))
        capital_at_risk = position_size_pct * 0.35
        freshness_summary = {
            "market_ready": len(market.data) >= 20,
            "order_book_ready": order_book is not None,
            "news_count": len(news.items) if news else 0,
            "social_count": len(social.items) if social else 0,
            "policy_count": len(policy.items) if policy else 0,
            "announcement_count": len(announcements.items) if announcements else 0,
            "notes": _replay_freshness_notes(order_book is not None, len(news.items) if news else 0, len(policy.items) if policy else 0),
            "watch_items": [
                "Historical replay is shadow-only and does not place orders.",
                "Portfolio state is read from the latest configured book.",
            ],
        }
        data = {
            "instrument": normalized,
            "requested_as_of": replay_as_of.isoformat(),
            "portfolio_name": portfolio_name,
            "asset_class": asset_class,
            "historical_move": move,
            "replayed_decision": final_action,
            "context_window_size": len(market.data),
            "news_count": len(news.items) if news else 0,
            "social_count": len(social.items) if social else 0,
            "announcement_count": len(announcements.items) if announcements else 0,
            "has_order_book": order_book is not None,
            "policy_count": len(policy.items) if policy else 0,
            "score_breakdown": score_breakdown,
            "decision_packet": {
                "instrument": normalized,
                "action": final_action,
                "confidence": confidence,
                "score": score,
                "thesis": _replay_thesis(final_action, move, score_breakdown),
                "entry_zone": f"{closes[0] * 0.995:.2f} - {closes[0] * 1.005:.2f}" if closes else "n/a",
                "stop_loss": f"{closes[0] * 0.97:.2f}" if closes else "n/a",
                "take_profit": f"{closes[0] * 1.05:.2f}" if closes else "n/a",
                "max_holding_period": "4h-7d" if asset_class == "crypto" else "1-10d",
                "position_size_pct": position_size_pct,
                "capital_at_risk": capital_at_risk,
                "kill_switch_reasons": veto_reasons,
            },
            "risk_verdict": {
                "allowed": allowed,
                "regime": (((risk.data or {}).get("regime") or {}).get("regime_label", "unknown")) if risk.status == "ready" else "unknown",
                "value_at_risk_95": (risk.data or {}).get("value_at_risk_95", 0.0) if risk.status == "ready" else 0.0,
                "concentration_risk": (risk.data or {}).get("concentration_risk", 0.0) if risk.status == "ready" else 0.0,
                "position_size_pct": position_size_pct,
                "capital_at_risk": capital_at_risk,
                "kill_switch_reasons": veto_reasons,
                "rationale": "Historical replay vetoes weak or structurally incomplete contexts before paper action.",
            },
            "freshness_summary": freshness_summary,
            "degrade_reason": "; ".join(veto_reasons) if veto_reasons else None,
            "portfolio_exposures": exposures.data if exposures.status == "ready" else None,
        }
        return SnapshotRead(
            status="ready",
            data=data,
            meta=SnapshotMeta(
                entity_type="replay_decision",
                entity_id=normalized,
                as_of=market.as_of,
                computed_at=market.computed_at,
                freshness="fresh",
                refresh_enqueued=False,
                feature_version="replay-decision-v1",
                provider_set=market.provider_set,
            ),
        )


async def _ensure_event_views(scope: str, store: Any, documents: Any) -> None:
    existing = await documents.get_event_feed(scope)
    if existing is not None:
        return
    records: list[tuple[str, Any]] = []
    for entity_id in _event_scope_entities(scope):
        for stream_type in ("news", "social", "announcements"):
            record = await documents.get_normalized_event_stream(stream_type, entity_id)
            if record is not None:
                records.append((stream_type, record))
    policy_scope = scope if scope in {"global", "india"} else "global"
    policy = await documents.get_policy_documents(policy_scope)
    if policy is not None:
        records.append(("policy", policy))

    events = _compose_real_event_feed(scope=scope, records=records)
    clusters = _cluster_real_events(events)
    provider_set = tuple(
        sorted(
            {
                provider
                for _, record in records
                for provider in getattr(record, "provider_set", ())
            }
        )
    )
    dominant = max(clusters, key=lambda item: float(item.get("importance", 0.0)), default=None)
    await documents.save_event_feed(scope=scope, items=events, provider_set=provider_set)
    await documents.save_event_clusters(scope=scope, items=clusters, provider_set=provider_set)
    await documents.save_event_pulse(
        scope=scope,
        data={
            "scope": scope,
            "headline": dominant.get("headline", "No normalized events available.") if dominant else "No normalized events available.",
            "event_count": len(events),
            "dominant_theme": dominant.get("category", "none") if dominant else "none",
            "average_urgency": mean([float(event.get("urgency", 0.0)) for event in events]) if events else 0.0,
            "average_importance": mean([float(event.get("importance", 0.0)) for event in events]) if events else 0.0,
            "highlights": [event.get("title", "") for event in events[:3]],
        },
        provider_set=provider_set,
    )


def _event_scope_entities(scope: str) -> list[str]:
    normalized = scope.lower()
    mapping = {
        "btc": ["X:BTCUSD", "BTC", "BTCUSD"],
        "india": ["IND", "NIFTY", "BANKNIFTY"],
        "us": ["SPY", "QQQ"],
        "global": [],
    }
    return mapping.get(normalized, [scope.upper()])


def _compose_real_event_feed(scope: str, records: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for stream_type, record in records:
        for item in list(getattr(record, "items", []))[:25]:
            title = (
                item.get("headline")
                or item.get("title")
                or item.get("event_id")
                or f"{stream_type} event"
            )
            events.append(
                {
                    "title": title,
                    "summary": item.get("summary") or item.get("description") or "",
                    "region": scope.upper(),
                    "category": "policy" if stream_type == "policy" else stream_type,
                    "entities": item.get("entity_ids") or item.get("entities") or [],
                    "urgency": float(item.get("relevance", item.get("urgency", 0.5)) or 0.5),
                    "importance": float(item.get("novelty", item.get("importance", 0.5)) or 0.5),
                    "published_at": item.get("published_at"),
                    "provider": item.get("provider"),
                }
            )
    events.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return events[:50]


def _cluster_real_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[str, dict[str, Any]] = {}
    for event in events:
        key = f"{event['region']}::{event['category']}"
        cluster = clusters.setdefault(
            key,
            {
                "cluster_id": key.lower().replace("::", "-"),
                "region": event["region"],
                "category": event["category"],
                "headline": event["title"],
                "event_count": 0,
                "importance": 0.0,
            },
        )
        cluster["event_count"] += 1
        cluster["importance"] = max(cluster["importance"], float(event.get("importance", 0.0)))
    return list(clusters.values())


async def _load_metric_series(
    store: Any,
    entity_type: str,
    metric: str,
    entity_id: str,
    limit: int,
) -> list[float]:
    if entity_type == "world_state":
        snapshots = await store.list_world_state_snapshots(limit=limit)
        return [_safe_float(getattr(snapshot.data, metric, 0.0)) for snapshot in snapshots]
    if entity_type == "company":
        snapshots = await store.list_company_snapshots(entity_id, limit=limit)
        return [_safe_float(getattr(snapshot.data, metric, 0.0)) for snapshot in snapshots]
    if entity_type == "country":
        snapshots = await store.list_country_snapshots(entity_id, limit=limit)
        return [_safe_float(getattr(snapshot.data, metric, 0.0)) for snapshot in snapshots]
    if entity_type == "market":
        ticks = await store.get_market_ticks(entity_id, limit=limit)
        if metric == "volume":
            return [float(tick.volume) for tick in ticks]
        return [_safe_float(getattr(tick, metric, 0.0)) for tick in ticks]
    return []


async def _compute_portfolio_metrics(store: Any, portfolio: dict[str, Any]) -> dict[str, Any]:
    positions = portfolio.get("positions", [])
    computed_positions: list[dict[str, Any]] = []
    total_market_value = 0.0
    asset_class_exposure: dict[str, float] = {}

    for position in positions:
        ticker = str(position["ticker"]).upper()
        quantity = _safe_float(position.get("quantity", 0.0))
        average_cost = _safe_float(position.get("average_cost", 0.0))
        asset_class = str(position.get("asset_class", "equity"))
        ticks = await store.get_market_ticks(ticker, limit=1)
        last_price = _safe_float(ticks[0].close) if ticks else average_cost
        market_value = quantity * last_price
        total_market_value += market_value
        asset_class_exposure[asset_class] = asset_class_exposure.get(asset_class, 0.0) + market_value
        computed_positions.append(
            {
                "ticker": ticker,
                "asset_class": asset_class,
                "quantity": quantity,
                "average_cost": average_cost,
                "last_price": last_price,
                "market_value": market_value,
            }
        )

    if total_market_value > 0:
        for position in computed_positions:
            position["weight"] = position["market_value"] / total_market_value
        for key, value in list(asset_class_exposure.items()):
            asset_class_exposure[key] = value / total_market_value
    else:
        for position in computed_positions:
            position["weight"] = 0.0

    estimated_daily_volatility = 0.0
    for position in computed_positions:
        ticker = position["ticker"]
        ticks = await store.get_market_ticks(ticker, limit=10)
        closes = [float(tick.close) for tick in reversed(ticks)]
        returns = [
            (current - previous) / previous
            for previous, current in zip(closes[:-1], closes[1:])
            if previous > 0
        ]
        asset_vol = pstdev(returns) if len(returns) >= 2 else 0.01
        estimated_daily_volatility += position["weight"] * asset_vol
    value_at_risk_95 = total_market_value * estimated_daily_volatility * 1.65

    computed_positions.sort(key=lambda item: item["weight"], reverse=True)
    return {
        "total_market_value": total_market_value,
        "positions": computed_positions,
        "asset_class_exposure": asset_class_exposure,
        "estimated_daily_volatility": estimated_daily_volatility,
        "value_at_risk_95": value_at_risk_95,
    }


def _provider_is_configured(name: str, settings: Any) -> bool:
    credential_map = {
        "massive": bool(getattr(settings, "market_api_key", "")),
        "fred": bool(getattr(settings, "fred_api_key", "")),
        "world_bank": bool(getattr(settings, "world_bank_base_url", "")),
        "oanda": bool(getattr(settings, "oanda_api_key", "")),
        "sec": bool(getattr(settings, "sec_user_agent", "")),
        "upstox": bool(getattr(settings, "upstox_api_key", "")),
        "coinapi": bool(getattr(settings, "coinapi_api_key", "")),
        "gdelt": bool(getattr(settings, "gdelt_base_url", "")),
        "reddit": bool(getattr(settings, "reddit_client_id", "")) and bool(getattr(settings, "reddit_client_secret", "")),
        "x": bool(getattr(settings, "x_bearer_token", "")),
        "rbi_rss": bool(getattr(settings, "rbi_rss_url", "")),
        "sebi_rss": bool(getattr(settings, "sebi_rss_url", "")),
        "nse_rss": bool(getattr(settings, "nse_rss_url", "")),
        "bse_rss": bool(getattr(settings, "bse_rss_url", "")),
    }
    return credential_map.get(name, True)


def _provider_coverage(name: str) -> str:
    if name in {"massive", "upstox", "coinapi", "oanda"}:
        return "market"
    if name in {"fred", "world_bank", "sec"}:
        return "fundamentals_macro"
    if name in {"gdelt", "reddit", "x"}:
        return "events"
    return "policy"


def _build_replay_score_breakdown(
    *,
    asset_class: str,
    historical_move: float,
    news_count: int,
    social_count: int,
    policy_count: int,
    has_order_book: bool,
) -> dict[str, float]:
    technical = max(0.0, min(1.0, 0.5 + (historical_move * 4)))
    news = min(news_count / 8, 1.0) * 0.5 + 0.25
    social = min(social_count / 10, 1.0) * 0.5 + 0.25
    policy = min(policy_count / 6, 1.0) * 0.4 + 0.3
    liquidity = 0.7 if has_order_book else 0.35
    if asset_class == "crypto":
        score = (technical * 0.30) + (liquidity * 0.25) + (news * 0.20) + (social * 0.15) + (policy * 0.10)
    else:
        fundamentals = 0.5
        score = (
            (technical * 0.25)
            + (fundamentals * 0.25)
            + (news * 0.20)
            + (social * 0.10)
            + (policy * 0.10)
            + (liquidity * 0.10)
        )
    return {
        "score": score,
        "technical": technical,
        "news": news,
        "social": social,
        "policy": policy,
        "liquidity": liquidity,
    }


def _replay_veto_reasons(
    *,
    asset_class: str,
    stance: str,
    score: float,
    has_order_book: bool,
    portfolio_risk: dict[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    if stance == "HOLD" or abs(score - 0.5) < 0.12:
        reasons.append("Replay conviction is too weak for a paper trade.")
    if asset_class == "crypto" and not has_order_book:
        reasons.append("Crypto replay is missing order-book evidence.")
    if portfolio_risk is None:
        reasons.append("Portfolio risk snapshot is unavailable.")
    elif float(portfolio_risk.get("concentration_risk", 0.0) or 0.0) > 0.55:
        reasons.append("Portfolio concentration is already above the allowed replay threshold.")
    return reasons


def _replay_freshness_notes(has_order_book: bool, news_count: int, policy_count: int) -> list[str]:
    notes = ["Market replay used historical bars at the requested timestamp."]
    if not has_order_book:
        notes.append("Level-2 depth was unavailable for the replay timestamp.")
    if news_count == 0:
        notes.append("No normalized news events were stored for this replay window.")
    if policy_count == 0:
        notes.append("No policy events were attached to the replay window.")
    return notes


def _replay_thesis(action: str, move: float, score_breakdown: dict[str, float]) -> str:
    direction = "positive" if move >= 0 else "negative"
    if action == "NO_TRADE":
        return "Historical context was measurable, but risk controls rejected trade deployment."
    return (
        f"Replay momentum was {direction} with technical score {score_breakdown['technical']:.2f} "
        f"and liquidity score {score_breakdown['liquidity']:.2f}."
    )

async def _snapshot_response(snapshot: Any, entity_type: str, entity_id: str, refreshes: Any) -> SnapshotRead[Any]:
    if snapshot is None:
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="cache_miss")
        return SnapshotRead(
            status="pending",
            data=None,
            meta=SnapshotMeta(
                entity_type=entity_type,
                entity_id=entity_id,
                as_of=None,
                computed_at=None,
                freshness="pending",
                refresh_enqueued=refresh_enqueued,
                suggested_retry_seconds=30,
            ),
        )

    freshness = FreshnessPolicy.classify(entity_type, snapshot.as_of)
    refresh_enqueued = False
    if freshness == "stale":
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="stale_snapshot")
    return SnapshotRead(
        status="ready",
        data=snapshot.data,
        meta=SnapshotMeta(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of=snapshot.as_of,
            computed_at=snapshot.computed_at,
            freshness=freshness,
            refresh_enqueued=refresh_enqueued,
            feature_version=snapshot.feature_version,
            provider_set=snapshot.provider_set,
        ),
    )


def _serialize_ticks(ticks: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for tick in ticks:
        items.append(
            {
                "ticker": tick.ticker,
                "asset_class": tick.asset_class.value,
                "timestamp": tick.timestamp.isoformat(),
                "open": str(tick.open),
                "high": str(tick.high),
                "low": str(tick.low),
                "close": str(tick.close),
                "volume": tick.volume,
            }
        )
    return items


def _parse_as_of(value: Any):
    from datetime import UTC, datetime

    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _manual_pending(entity_type: str, entity_id: str) -> SnapshotRead[Any]:
    return SnapshotRead(
        status="pending",
        data=None,
        meta=SnapshotMeta(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of=None,
            computed_at=None,
            freshness="pending",
            refresh_enqueued=False,
            suggested_retry_seconds=0,
        ),
    )


async def _collection_response(record: Any, entity_type: str, entity_id: str, refreshes: Any) -> SnapshotRead[list[dict[str, Any]]]:
    if record is None:
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="cache_miss")
        return SnapshotRead(
            status="pending",
            data=None,
            meta=SnapshotMeta(
                entity_type=entity_type,
                entity_id=entity_id,
                as_of=None,
                computed_at=None,
                freshness="pending",
                refresh_enqueued=refresh_enqueued,
                suggested_retry_seconds=30,
            ),
        )

    freshness = FreshnessPolicy.classify(entity_type, record.as_of)
    refresh_enqueued = False
    if freshness == "stale":
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="stale_snapshot")
    return SnapshotRead(
        status="ready",
        data=list(record.items),
        meta=SnapshotMeta(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of=record.as_of,
            computed_at=record.computed_at,
            freshness=freshness,
            refresh_enqueued=refresh_enqueued,
            feature_version=record.feature_version,
            provider_set=record.provider_set,
        ),
    )
