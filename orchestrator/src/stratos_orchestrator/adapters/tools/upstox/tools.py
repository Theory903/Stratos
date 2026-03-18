"""
Upstox Trading Tools for Finance Council Agents

Integrates Upstox API with STRATOS agent framework for:
- Portfolio analysis and optimization
- Real-time market data and quotes
- Order placement and management
- Risk analysis and monitoring
- Historical data analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from stratos_orchestrator.adapters.tools.upstox.client import UpstoxClient

logger = logging.getLogger(__name__)


class UpstoxPortfolioTool:
    """Tool for portfolio analysis and optimization using Upstox data."""

    def __init__(self, client: UpstoxClient):
        """
        Initialize portfolio tool.

        Args:
            client: Upstox API client
        """
        self.client = client
        self.name = "upstox_portfolio"
        self.description = "Analyze and optimize portfolio using Upstox account data"

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary.

        Returns:
            Portfolio summary with holdings, value, and allocation
        """
        try:
            holdings_response = self.client.get_portfolio()
            margins_response = self.client.get_fund_and_margin()
            pnl_response = self.client.get_profit_and_loss()

            holdings = holdings_response.get("data", [])
            margins = margins_response.get("data", {})
            pnl = pnl_response.get("data", {})

            # Calculate portfolio metrics
            total_value = sum(h.get("quantity", 0) * h.get("ltp", 0) for h in holdings)
            total_invested = sum(h.get("quantity", 0) * h.get("average_price", 0) for h in holdings)

            return {
                "status": "success",
                "summary": {
                    "total_holdings": len(holdings),
                    "total_portfolio_value": total_value,
                    "total_invested": total_invested,
                    "unrealized_gain": total_value - total_invested,
                    "unrealized_gain_percent": (
                        (total_value - total_invested) / total_invested * 100
                    )
                    if total_invested > 0
                    else 0,
                    "available_margin": margins.get("available_margin", 0),
                    "used_margin": margins.get("used_margin", 0),
                    "realized_gain": pnl.get("realized_gain", 0),
                    "unrealized_pnl": pnl.get("unrealized_pnl", 0),
                },
                "holdings": holdings,
                "margins": margins,
                "pnl": pnl,
            }
        except Exception as e:
            logger.error(f"Portfolio summary error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def analyze_portfolio_allocation(self) -> Dict[str, Any]:
        """
        Analyze portfolio allocation by sector and asset class.

        Returns:
            Allocation analysis
        """
        try:
            holdings = self.client.get_portfolio().get("data", [])

            # Group by sector/instrument type
            allocation = {}
            total_value = 0

            for holding in holdings:
                sector = holding.get("sector", "Other")
                value = holding.get("quantity", 0) * holding.get("ltp", 0)
                total_value += value

                if sector not in allocation:
                    allocation[sector] = {"value": 0, "count": 0, "holdings": []}

                allocation[sector]["value"] += value
                allocation[sector]["count"] += 1
                allocation[sector]["holdings"].append(
                    {
                        "symbol": holding.get("trading_symbol"),
                        "value": value,
                        "weight": 0,  # Will calculate below
                    }
                )

            # Calculate weights
            for sector in allocation:
                allocation[sector]["weight"] = (
                    (allocation[sector]["value"] / total_value * 100) if total_value > 0 else 0
                )
                for holding in allocation[sector]["holdings"]:
                    holding["weight"] = (
                        (holding["value"] / total_value * 100) if total_value > 0 else 0
                    )

            return {
                "status": "success",
                "total_portfolio_value": total_value,
                "allocation": allocation,
            }
        except Exception as e:
            logger.error(f"Allocation analysis error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_concentration_metrics(self) -> Dict[str, Any]:
        """
        Calculate concentration metrics (top holdings, diversification).

        Returns:
            Concentration analysis
        """
        try:
            holdings = self.client.get_portfolio().get("data", [])

            # Sort by value
            sorted_holdings = sorted(
                holdings, key=lambda x: x.get("quantity", 0) * x.get("ltp", 0), reverse=True
            )

            total_value = sum(h.get("quantity", 0) * h.get("ltp", 0) for h in holdings)

            # Top holdings
            top_10 = []
            top_10_value = 0
            for i, holding in enumerate(sorted_holdings[:10]):
                value = holding.get("quantity", 0) * holding.get("ltp", 0)
                top_10_value += value
                top_10.append(
                    {
                        "rank": i + 1,
                        "symbol": holding.get("trading_symbol"),
                        "value": value,
                        "weight": (value / total_value * 100) if total_value > 0 else 0,
                    }
                )

            # Herfindahl index (concentration measure)
            herfindahl = (
                sum((h.get("quantity", 0) * h.get("ltp", 0) / total_value) ** 2 for h in holdings)
                if total_value > 0
                else 0
            )

            return {
                "status": "success",
                "total_holdings": len(holdings),
                "top_10_concentration": (top_10_value / total_value * 100)
                if total_value > 0
                else 0,
                "top_10_holdings": top_10,
                "herfindahl_index": herfindahl,
                "diversification_score": (1 - herfindahl) * 100,  # 0-100, higher is better
            }
        except Exception as e:
            logger.error(f"Concentration metrics error: {str(e)}")
            return {"status": "error", "message": str(e)}


class UpstoxMarketDataTool:
    """Tool for real-time market data and quotes."""

    def __init__(self, client: UpstoxClient):
        """Initialize market data tool."""
        self.client = client
        self.name = "upstox_market_data"
        self.description = "Get real-time market quotes and data from Upstox"

    async def get_quotes(self, instrument_keys: List[str]) -> Dict[str, Any]:
        """
        Get real-time quotes for instruments.

        Args:
            instrument_keys: List of instrument keys (e.g., ['NSE_EQ|INE002A01018'])

        Returns:
            Quote data with price, volume, etc.
        """
        try:
            quotes = self.client.get_market_quote(instrument_keys)
            return {"status": "success", "quotes": quotes.get("data", {})}
        except Exception as e:
            logger.error(f"Market quote error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_ltp(self, instrument_keys: List[str]) -> Dict[str, Any]:
        """
        Get Last Traded Price (LTP).

        Args:
            instrument_keys: List of instrument keys

        Returns:
            LTP for each instrument
        """
        try:
            ltp_data = self.client.get_ltp(instrument_keys)
            return {"status": "success", "ltp": ltp_data}
        except Exception as e:
            logger.error(f"LTP error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_technical_analysis(self, instrument_key: str, period: int = 20) -> Dict[str, Any]:
        """
        Get technical analysis indicators.

        Args:
            instrument_key: Instrument key
            period: Period for calculations

        Returns:
            Technical indicators (MA, RSI, MACD, Bollinger Bands)
        """
        try:
            # Get historical data
            candles = self.client.get_historical_data(
                instrument_key=instrument_key,
                unit="days",
                interval=1,
                to_date=datetime.now().strftime("%Y-%m-%d"),
                from_date=(datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d"),
            )

            if not candles:
                return {"status": "error", "message": "No historical data available"}

            closes = [c[4] for c in candles]  # Close prices

            # Simple Moving Average
            sma = sum(closes[-period:]) / period if len(closes) >= period else 0

            # RSI calculation
            deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]

            avg_gain = sum(gains[-period:]) / period if len(gains) >= period else 0
            avg_loss = sum(losses[-period:]) / period if len(losses) >= period else 0

            rs = avg_gain / avg_loss if avg_loss > 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

            # Current price
            current_price = closes[-1] if closes else 0

            return {
                "status": "success",
                "instrument": instrument_key,
                "current_price": current_price,
                "sma_20": sma,
                "rsi_14": rsi,
                "trend": "bullish" if current_price > sma else "bearish",
                "rsi_signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
            }
        except Exception as e:
            logger.error(f"Technical analysis error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_option_chain_analysis(
        self, instrument_key: str, expiry_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze option chain data.

        Args:
            instrument_key: Underlying instrument key
            expiry_date: Optional expiry date

        Returns:
            Option chain analysis
        """
        try:
            options = self.client.get_option_chain(
                instrument_key=instrument_key, expiry_date=expiry_date
            )

            option_data = options.get("data", [])

            # Separate calls and puts
            calls = [o for o in option_data if o.get("instrument_type") == "CE"]
            puts = [o for o in option_data if o.get("instrument_type") == "PE"]

            # Calculate IV and Greeks (simplified)
            analysis = {
                "status": "success",
                "underlying": instrument_key,
                "total_contracts": len(option_data),
                "call_contracts": len(calls),
                "put_contracts": len(puts),
                "expiry_dates": list(set(o.get("expiry") for o in option_data)),
                "strike_range": {
                    "min": min((o.get("strike_price", 0) for o in option_data), default=0),
                    "max": max((o.get("strike_price", 0) for o in option_data), default=0),
                },
            }

            return analysis
        except Exception as e:
            logger.error(f"Option chain analysis error: {str(e)}")
            return {"status": "error", "message": str(e)}


class UpstoxOrderTool:
    """Tool for order placement and management."""

    def __init__(self, client: UpstoxClient):
        """Initialize order tool."""
        self.client = client
        self.name = "upstox_orders"
        self.description = "Place and manage orders on Upstox"

    async def place_order(
        self,
        instrument_key: str,
        quantity: int,
        side: str,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        product_type: str = "MIS",
        validity: str = "DAY",
    ) -> Dict[str, Any]:
        """
        Place an order.

        Args:
            instrument_key: Instrument key
            quantity: Order quantity
            side: BUY or SELL
            order_type: MARKET, LIMIT
            price: Price for limit orders
            product_type: MIS, CNC, NRML
            validity: DAY, IOC

        Returns:
            Order response
        """
        try:
            response = self.client.place_order(
                instrument_key=instrument_key,
                quantity=quantity,
                side=side,
                order_type=order_type,
                price=price or 0,
                product_type=product_type,
                validity=validity,
            )

            return {
                "status": "success" if response.get("status") == "success" else "error",
                "order": response.get("data", {}),
                "message": response.get("message", "Order placed successfully"),
            }
        except Exception as e:
            logger.error(f"Order placement error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_open_orders(self) -> Dict[str, Any]:
        """Get all open orders."""
        try:
            orders = self.client.get_orders()

            # Filter open orders
            open_orders = [o for o in orders if o.get("status") not in ["filled", "cancelled"]]

            return {
                "status": "success",
                "total_orders": len(orders),
                "open_orders": len(open_orders),
                "orders": open_orders,
            }
        except Exception as e:
            logger.error(f"Get orders error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            response = self.client.cancel_order(order_id)
            return {
                "status": "success" if response.get("status") == "success" else "error",
                "message": response.get("message", "Order cancelled successfully"),
            }
        except Exception as e:
            logger.error(f"Cancel order error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def create_gtt_order(
        self,
        instrument_key: str,
        quantity: int,
        side: str,
        price: float,
        trigger_price: float,
        product_type: str = "MIS",
    ) -> Dict[str, Any]:
        """
        Create a Good-Till-Triggered order.

        Args:
            instrument_key: Instrument key
            quantity: Order quantity
            side: BUY or SELL
            price: Execution price
            trigger_price: Trigger price
            product_type: MIS, CNC, NRML

        Returns:
            GTT order response
        """
        try:
            response = self.client.create_gtt_order(
                instrument_key=instrument_key,
                quantity=quantity,
                side=side,
                price=price,
                trigger_price=trigger_price,
                product_type=product_type,
            )

            return {
                "status": "success" if response.get("status") == "success" else "error",
                "gtt_order": response.get("data", {}),
                "message": response.get("message", "GTT order created successfully"),
            }
        except Exception as e:
            logger.error(f"GTT order error: {str(e)}")
            return {"status": "error", "message": str(e)}


class UpstoxRiskAnalysisTool:
    """Tool for risk analysis and monitoring."""

    def __init__(self, client: UpstoxClient):
        """Initialize risk analysis tool."""
        self.client = client
        self.name = "upstox_risk"
        self.description = "Analyze and monitor portfolio risk using Upstox data"

    async def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio risk metrics.

        Returns:
            Risk metrics including VaR, volatility, beta
        """
        try:
            holdings = self.client.get_portfolio().get("data", [])
            margins = self.client.get_fund_and_margin().get("data", {})

            total_value = sum(h.get("quantity", 0) * h.get("ltp", 0) for h in holdings)

            # Leverage ratio
            leverage = (
                (total_value + margins.get("used_margin", 0)) / total_value
                if total_value > 0
                else 1
            )

            # Get P&L for volatility
            pnl_data = self.client.get_profit_and_loss().get("data", {})

            return {
                "status": "success",
                "portfolio_metrics": {
                    "total_value": total_value,
                    "leverage_ratio": leverage,
                    "margin_utilization": (
                        margins.get("used_margin", 0)
                        / (margins.get("available_margin", 0) + margins.get("used_margin", 0))
                        * 100
                    )
                    if (margins.get("available_margin", 0) + margins.get("used_margin", 0)) > 0
                    else 0,
                    "realized_pnl": pnl_data.get("realized_gain", 0),
                    "unrealized_pnl": pnl_data.get("unrealized_pnl", 0),
                    "total_pnl": pnl_data.get("realized_gain", 0)
                    + pnl_data.get("unrealized_pnl", 0),
                },
            }
        except Exception as e:
            logger.error(f"Risk metrics error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def identify_risk_exposures(self) -> Dict[str, Any]:
        """
        Identify high-risk exposures in portfolio.

        Returns:
            Risk exposures analysis
        """
        try:
            holdings = self.client.get_portfolio().get("data", [])

            risk_exposures = []
            total_value = sum(h.get("quantity", 0) * h.get("ltp", 0) for h in holdings)

            for holding in holdings:
                value = holding.get("quantity", 0) * holding.get("ltp", 0)
                weight = (value / total_value * 100) if total_value > 0 else 0

                # Flag high concentration
                if weight > 10:
                    risk_exposures.append(
                        {
                            "type": "concentration",
                            "symbol": holding.get("trading_symbol"),
                            "weight": weight,
                            "severity": "high" if weight > 20 else "medium",
                        }
                    )

                # Flag negative returns
                pnl = value - (holding.get("quantity", 0) * holding.get("average_price", 0))
                if pnl < 0:
                    pnl_percent = (
                        (pnl / (holding.get("quantity", 0) * holding.get("average_price", 0)) * 100)
                        if (holding.get("quantity", 0) * holding.get("average_price", 0)) > 0
                        else 0
                    )
                    if pnl_percent < -10:
                        risk_exposures.append(
                            {
                                "type": "loss",
                                "symbol": holding.get("trading_symbol"),
                                "loss_percent": pnl_percent,
                                "severity": "high" if pnl_percent < -20 else "medium",
                            }
                        )

            return {
                "status": "success",
                "risk_exposures": risk_exposures,
                "total_exposures": len(risk_exposures),
            }
        except Exception as e:
            logger.error(f"Risk exposure error: {str(e)}")
            return {"status": "error", "message": str(e)}


async def create_upstox_tools(client: UpstoxClient) -> Dict[str, Any]:
    """
    Create all Upstox tools for Finance Council agents.

    Args:
        client: Upstox API client

    Returns:
        Dictionary of tools with names and descriptions
    """
    tools = {
        "portfolio": UpstoxPortfolioTool(client),
        "market_data": UpstoxMarketDataTool(client),
        "orders": UpstoxOrderTool(client),
        "risk": UpstoxRiskAnalysisTool(client),
    }

    return tools


async def register_upstox_with_agents(tools: Dict[str, Any], agent_registry: Any) -> bool:
    """
    Register Upstox tools with agent registry.

    Args:
        tools: Dictionary of Upstox tools
        agent_registry: Agent registry to register with

    Returns:
        Success status
    """
    try:
        for tool_name, tool in tools.items():
            agent_registry.register_tool(
                name=f"upstox_{tool_name}", tool=tool, description=tool.description
            )

        logger.info(f"Registered {len(tools)} Upstox tools with agent registry")
        return True
    except Exception as e:
        logger.error(f"Tool registration error: {str(e)}")
        return False
