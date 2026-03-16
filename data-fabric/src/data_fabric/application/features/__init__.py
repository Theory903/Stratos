"""Feature-building use cases fed by raw provider documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from statistics import pstdev
from typing import Any

from data_fabric.domain.entities import CompanyProfile, CountryProfile, MarketTick

from data_fabric.application.ingestion import normalize_market_bars


def _clamp(value: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(slots=True)
class FeatureBuilderUseCase:
    """Compute versioned feature tables from raw provider documents."""

    store: Any
    documents: Any
    events: Any

    async def execute(self, message: dict[str, Any]) -> None:
        provider = str(message["provider"])
        entity_type = str(message["entity_type"])
        entity_id = str(message["entity_id"])

        if provider == "fred":
            document = await self.documents.get_latest_provider_document(provider, entity_type, entity_id, "macro_series")
            if not document:
                return
            await self.store.save_macro_series_points(document["payload"]["observations"], provider_set=("fred",))
            await self.events.publish(
                topic="feature.build.completed",
                key=f"{entity_type}:{entity_id}",
                payload={"domain": "world_state", "entity_id": entity_id},
            )
            return

        if provider == "world_bank":
            document = await self.documents.get_latest_provider_document(provider, entity_type, entity_id, "country_profile")
            if not document:
                return
            profile = CountryProfile(
                country_code=entity_id.upper(),
                debt_gdp=float(document["payload"]["debt_gdp"]),
                fx_reserves=float(document["payload"]["fx_reserves"]),
                fiscal_deficit=float(document["payload"]["fiscal_deficit"]),
                political_stability=float(document["payload"]["political_stability"]),
                currency_volatility=float(document["payload"]["currency_volatility"]),
                stored_at=datetime.now(timezone.utc),
            )
            await self.store.save_country_indicator_points(
                country_code=entity_id.upper(),
                indicators={
                    "debt_gdp": profile.debt_gdp,
                    "fx_reserves": profile.fx_reserves,
                    "fiscal_deficit": profile.fiscal_deficit,
                    "political_stability": profile.political_stability,
                    "currency_volatility": profile.currency_volatility,
                },
                provider_set=("world_bank",),
            )
            await self.store.save_country_snapshot(
                profile,
                feature_version="country-v1",
                provider_set=("world_bank",),
            )
            await self.events.publish(
                topic="feature.build.completed",
                key=f"{entity_type}:{entity_id}",
                payload={"domain": "country", "entity_id": entity_id.upper()},
            )
            return

        if provider == "sec":
            document = await self.documents.get_latest_provider_document(provider, entity_type, entity_id, "company_bundle")
            if not document:
                return
            companyfacts = document["payload"].get("companyfacts", {})
            submissions = document["payload"].get("submissions", {})
            name = str(submissions.get("name") or companyfacts.get("entityName") or entity_id.upper())
            metrics = self._compute_company_metrics(companyfacts)
            profile = CompanyProfile(
                ticker=entity_id.upper(),
                name=name,
                earnings_quality=metrics["earnings_quality"],
                leverage_ratio=metrics["leverage_ratio"],
                free_cash_flow_stability=metrics["free_cash_flow_stability"],
                fraud_score=metrics["fraud_score"],
                moat_score=metrics["moat_score"],
                stored_at=datetime.now(timezone.utc),
            )
            await self.store.save_company_fact_points(
                ticker=entity_id.upper(),
                facts=metrics["fact_points"],
                provider_set=("sec",),
            )
            await self.store.save_company_snapshot(
                profile,
                feature_version="company-v1",
                provider_set=("sec",),
            )
            await self.events.publish(
                topic="feature.build.completed",
                key=f"{entity_type}:{entity_id}",
                payload={"domain": "company", "entity_id": entity_id.upper()},
            )
            return

        if provider == "massive":
            document = await self.documents.get_latest_provider_document(provider, entity_type, entity_id, "market_bars")
            if not document:
                return
            bars = normalize_market_bars(document["payload"].get("bars", []))
            await self.store.save_market_ticks(
                bars,
                feature_version="market-bars-v1",
                provider_set=("massive",),
            )
            await self.events.publish(
                topic="feature.build.completed",
                key=f"{entity_type}:{entity_id}",
                payload={"domain": "market", "entity_id": entity_id.upper()},
            )

    def _compute_company_metrics(self, companyfacts: dict[str, Any]) -> dict[str, Any]:
        revenues = self._fact_series(companyfacts, "Revenues")
        net_income = self._fact_series(companyfacts, "NetIncomeLoss")
        operating_cash_flow = self._fact_series(companyfacts, "NetCashProvidedByUsedInOperatingActivities")
        assets = self._fact_series(companyfacts, "Assets")
        liabilities = self._fact_series(companyfacts, "Liabilities")
        gross_profit = self._fact_series(companyfacts, "GrossProfit")
        free_cash_flow = self._fact_series(companyfacts, "NetCashProvidedByUsedInOperatingActivities")

        latest_revenue = revenues[0]["value"] if revenues else 0.0
        prior_revenue = revenues[1]["value"] if len(revenues) > 1 else latest_revenue
        revenue_growth = 0.0 if prior_revenue == 0 else (latest_revenue - prior_revenue) / abs(prior_revenue)

        latest_income = net_income[0]["value"] if net_income else 0.0
        latest_ocf = operating_cash_flow[0]["value"] if operating_cash_flow else 0.0
        accrual_gap = 0.0 if latest_income == 0 else abs(latest_ocf - latest_income) / abs(latest_income)
        earnings_quality = _clamp(1.0 - min(accrual_gap, 1.0))

        latest_assets = assets[0]["value"] if assets else 1.0
        latest_liabilities = liabilities[0]["value"] if liabilities else 0.0
        leverage_ratio = _clamp(latest_liabilities / latest_assets if latest_assets else 0.0)

        fcf_values = [point["value"] for point in free_cash_flow[:8] if point["value"] is not None]
        if len(fcf_values) >= 2:
            mean_fcf = sum(abs(value) for value in fcf_values) / len(fcf_values) or 1.0
            free_cash_flow_stability = _clamp(1.0 - min(pstdev(fcf_values) / mean_fcf, 1.0))
        else:
            free_cash_flow_stability = 0.5

        latest_gross_profit = gross_profit[0]["value"] if gross_profit else 0.0
        gross_margin = 0.0 if latest_revenue == 0 else latest_gross_profit / latest_revenue
        moat_score = _clamp((gross_margin * 0.7) + (_clamp(revenue_growth + 0.2, maximum=0.4) / 0.4 * 0.3))

        fraud_score = _clamp((1.0 - earnings_quality) * 0.6 + leverage_ratio * 0.4)

        fact_points = [
            {"fact_name": "revenue", "period_end": point["period_end"], "value": point["value"], "unit": point["unit"]}
            for point in revenues[:8]
        ]
        fact_points.extend(
            {"fact_name": "net_income", "period_end": point["period_end"], "value": point["value"], "unit": point["unit"]}
            for point in net_income[:8]
        )
        fact_points.extend(
            {"fact_name": "assets", "period_end": point["period_end"], "value": point["value"], "unit": point["unit"]}
            for point in assets[:4]
        )

        return {
            "earnings_quality": earnings_quality,
            "leverage_ratio": leverage_ratio,
            "free_cash_flow_stability": free_cash_flow_stability,
            "fraud_score": fraud_score,
            "moat_score": moat_score,
            "fact_points": fact_points,
        }

    @staticmethod
    def _fact_series(companyfacts: dict[str, Any], concept: str) -> list[dict[str, Any]]:
        units = (
            companyfacts.get("facts", {})
            .get("us-gaap", {})
            .get(concept, {})
            .get("units", {})
        )
        preferred = units.get("USD") or units.get("USD/shares") or next(iter(units.values()), [])
        series: list[dict[str, Any]] = []
        for row in preferred:
            value = row.get("val")
            end = row.get("end")
            if value is None or end is None:
                continue
            series.append(
                {
                    "value": float(value),
                    "period_end": datetime.fromisoformat(end).date(),
                    "unit": row.get("uom", "USD"),
                }
            )
        series.sort(key=lambda item: item["period_end"], reverse=True)
        return series

