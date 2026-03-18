"""Finance context loading and freshness summarization."""

from __future__ import annotations

from typing import Any

from stratos_orchestrator.adapters.tools.registry import ToolRegistry


class FinanceContextLoader:
    """Load a joined finance context from the available tool surface."""

    def __init__(self, tools: ToolRegistry) -> None:
        self._tools = tools

    async def load(self, instrument: str) -> dict[str, Any]:
        if self._tools.has_tool("decision_context_analyze"):
            try:
                context = await self._tools.execute("decision_context_analyze", {"instrument": instrument, "portfolio_name": "primary"})
                await self._augment_with_runtime_checks(context, instrument)
                return context
            except Exception:
                pass

        market = await self._execute_if_present("market_analyze", {"ticker": instrument, "limit": 20})
        news = await self._execute_if_present("company_news_analyze", {"ticker": instrument})
        social = await self._execute_if_present("social_analyze", {"entity": instrument})
        portfolio = await self._execute_if_present("portfolio_analyze", {"name": "primary"})
        order_book = await self._execute_if_present("order_book_analyze", {"instrument": instrument})
        policy = await self._execute_if_present("policy_events_analyze", {"scope": "india" if self._is_india_instrument(instrument) else "global"})
        provider_health = await self._execute_if_present("provider_health_analyze", {})
        company = {}
        if self._needs_company_fundamentals(instrument):
            company = await self._execute_if_present("company_analyze", {"ticker": instrument})
        portfolio_snapshot = portfolio if isinstance(portfolio, dict) else {}
        portfolio_exposures = self._derive_portfolio_exposures(portfolio_snapshot)
        market_points = market.get("bars", []) if isinstance(market, dict) else []
        replay_summary = await self._replay_summary(instrument, market_points)

        return {
            "market": market,
            "company": company,
            "news": news.get("items", []) if isinstance(news, dict) else [],
            "social": social.get("items", []) if isinstance(social, dict) else [],
            "portfolio": portfolio_snapshot,
            "portfolio_exposures": portfolio_exposures,
            "portfolio_risk": portfolio.get("risk") if isinstance(portfolio, dict) else None,
            "order_book": order_book.get("snapshot") if isinstance(order_book, dict) else None,
            "policy": policy.get("items", []) if isinstance(policy, dict) else [],
            "provider_health": provider_health,
            "replay_summary": replay_summary,
        }

    async def _execute_if_present(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._tools.has_tool(tool_name):
            return {}
        try:
            result = await self._tools.execute(tool_name, arguments)
        except Exception:
            return {}
        return result if isinstance(result, dict) else {}

    async def _augment_with_runtime_checks(self, context: dict[str, Any], instrument: str) -> None:
        provider_health = await self._execute_if_present("provider_health_analyze", {})
        replay_summary = await self._replay_summary(instrument, context.get("market", []))
        context["provider_health"] = provider_health
        context["replay_summary"] = replay_summary

    async def _replay_summary(self, instrument: str, market_points: list[dict[str, Any]]) -> dict[str, Any]:
        if not self._tools.has_tool("replay_decision_analyze"):
            return {}
        as_of = self._latest_market_timestamp(market_points)
        if not as_of:
            return {}
        replay = await self._execute_if_present(
            "replay_decision_analyze",
            {"instrument": instrument, "as_of": as_of, "portfolio_name": "primary"},
        )
        if not replay:
            return {}
        risk_verdict = replay.get("risk_verdict") if isinstance(replay.get("risk_verdict"), dict) else {}
        decision_packet = replay.get("decision_packet") if isinstance(replay.get("decision_packet"), dict) else {}
        veto_reasons = risk_verdict.get("kill_switch_reasons") or decision_packet.get("kill_switch_reasons") or []
        return {
            "as_of": replay.get("requested_as_of"),
            "action": replay.get("replayed_decision"),
            "confidence": decision_packet.get("confidence"),
            "realized_move": replay.get("historical_move"),
            "outcome_label": "accepted" if risk_verdict.get("allowed", False) else "vetoed",
            "veto_reason": veto_reasons[0] if veto_reasons else None,
            "notes": replay.get("freshness_summary", {}).get("notes", []) if isinstance(replay.get("freshness_summary"), dict) else [],
        }

    @staticmethod
    def _needs_company_fundamentals(instrument: str) -> bool:
        return not instrument.startswith(("X:", "FX:", "INDEX:"))

    @staticmethod
    def _is_india_instrument(instrument: str) -> bool:
        return instrument.startswith(("NSE", "BSE", "INDEX:NIFTY", "INDEX:BANKNIFTY", "INDEX:SENSEX", "INDEX:INDIAVIX"))

    @staticmethod
    def _latest_market_timestamp(market_points: list[dict[str, Any]]) -> str | None:
        for point in market_points:
            timestamp = point.get("timestamp")
            if timestamp:
                return str(timestamp)
        return None

    @staticmethod
    def _derive_portfolio_exposures(portfolio: dict[str, Any]) -> dict[str, Any] | None:
        positions = portfolio.get("positions", []) if isinstance(portfolio, dict) else []
        if not isinstance(positions, list) or not positions:
            return None
        total_weight = 0.0
        asset_class_exposure: dict[str, float] = {}
        top_positions: list[dict[str, Any]] = []
        for position in positions:
            if not isinstance(position, dict):
                continue
            weight = float(position.get("weight", 0.0) or 0.0)
            asset_class = str(position.get("asset_class", "equity"))
            total_weight += weight
            asset_class_exposure[asset_class] = asset_class_exposure.get(asset_class, 0.0) + weight
            top_positions.append({"ticker": str(position.get("ticker", "")).upper(), "weight": weight})
        if total_weight <= 0:
            return None
        return {
            "asset_class_exposure": asset_class_exposure,
            "top_positions": sorted(top_positions, key=lambda item: float(item.get("weight", 0.0)), reverse=True),
        }


class FreshnessGate:
    """Summarize the readiness and freshness of finance inputs."""

    def summarize(self, context: dict[str, Any]) -> dict[str, Any]:
        notes: list[str] = []
        watch_items: list[str] = []
        market = context.get("market")
        if not market:
            notes.append("Primary market snapshot is missing.")
        order_book = context.get("order_book")
        if order_book is None:
            notes.append("Order book snapshot unavailable; microstructure confidence is reduced.")
        for label in ("news", "social", "exchange_announcements", "policy"):
            if not context.get(label):
                notes.append(f"{label.replace('_', ' ').title()} stream is missing or stale.")
            else:
                watch_items.append(f"{label.replace('_', ' ').title()} active")
        return {
            "market_ready": bool(market),
            "order_book_ready": order_book is not None,
            "news_count": len(context.get("news", [])),
            "social_count": len(context.get("social", [])),
            "policy_count": len(context.get("policy", [])),
            "notes": notes or ["All primary finance feeds returned data."],
            "watch_items": watch_items,
        }
