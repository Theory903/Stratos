"""
Upstox Integration Module for STRATOS Orchestrator

Provides complete integration with Upstox trading platform:
- Real-time market data and quotes
- Portfolio management and analysis
- Order placement and execution
- Risk monitoring and analysis
- Option chain analysis
- Historical data and technical analysis

This module bridges STRATOS Finance Council agents with Upstox trading capabilities.
"""

import logging
from typing import Any, Dict, Optional

from stratos_orchestrator.adapters.tools.upstox.client import UpstoxClient
from stratos_orchestrator.adapters.tools.upstox.tools import (
    UpstoxMarketDataTool,
    UpstoxOrderTool,
    UpstoxPortfolioTool,
    UpstoxRiskAnalysisTool,
    create_upstox_tools,
    register_upstox_with_agents,
)

logger = logging.getLogger(__name__)


class UpstoxIntegration:
    """
    Main integration class for Upstox platform.

    Manages client initialization, tool creation, and agent registration.
    Provides a single entry point for all Upstox operations.
    """

    def __init__(
        self,
        access_token: str,
        api_key: Optional[str] = None,
        sandbox_mode: bool = True,
        timeout: int = 30,
    ):
        """
        Initialize Upstox integration.

        Args:
            access_token: Upstox OAuth access token
            api_key: Optional API key for additional features
            sandbox_mode: Use sandbox environment for testing
            timeout: Request timeout in seconds
        """
        self.access_token = access_token
        self.api_key = api_key
        self.sandbox_mode = sandbox_mode
        self.timeout = timeout

        # Initialize client
        try:
            self.client = UpstoxClient(
                api_key=api_key or "demo",
                access_token=access_token,
                sandbox_mode=sandbox_mode,
                timeout=timeout,
            )
            logger.info(f"Upstox client initialized (sandbox={sandbox_mode})")
        except Exception as e:
            logger.error(f"Failed to initialize Upstox client: {str(e)}")
            raise

        # Tool instances
        self.portfolio_tool: Optional[UpstoxPortfolioTool] = None
        self.market_data_tool: Optional[UpstoxMarketDataTool] = None
        self.order_tool: Optional[UpstoxOrderTool] = None
        self.risk_tool: Optional[UpstoxRiskAnalysisTool] = None
        self.tools: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """
        Initialize all tools and verify connection.

        Returns:
            True if initialization successful
        """
        try:
            # Verify token is valid
            profile = self.client.get_profile()
            if profile.get("status") != "success":
                logger.error("Failed to verify Upstox token")
                return False

            logger.info(
                f"Connected to Upstox account: {profile.get('data', {}).get('email', 'unknown')}"
            )

            # Create tool instances
            self.portfolio_tool = UpstoxPortfolioTool(self.client)
            self.market_data_tool = UpstoxMarketDataTool(self.client)
            self.order_tool = UpstoxOrderTool(self.client)
            self.risk_tool = UpstoxRiskAnalysisTool(self.client)

            # Create tools dictionary
            self.tools = await create_upstox_tools(self.client)

            logger.info("Upstox integration initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Upstox initialization failed: {str(e)}")
            return False

    async def register_with_agents(self, agent_registry: Any) -> bool:
        """
        Register all tools with agent registry.

        Args:
            agent_registry: Agent registry instance

        Returns:
            True if registration successful
        """
        try:
            success = await register_upstox_with_agents(self.tools, agent_registry)
            if success:
                logger.info("Upstox tools registered with agents")
            return success
        except Exception as e:
            logger.error(f"Tool registration failed: {str(e)}")
            return False

    # ==================== Portfolio Operations ====================

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
        if not self.portfolio_tool:
            return {"status": "error", "message": "Portfolio tool not initialized"}
        return await self.portfolio_tool.get_portfolio_summary()

    async def get_portfolio_allocation(self) -> Dict[str, Any]:
        """Get portfolio allocation analysis."""
        if not self.portfolio_tool:
            return {"status": "error", "message": "Portfolio tool not initialized"}
        return await self.portfolio_tool.analyze_portfolio_allocation()

    async def get_portfolio_concentration(self) -> Dict[str, Any]:
        """Get portfolio concentration metrics."""
        if not self.portfolio_tool:
            return {"status": "error", "message": "Portfolio tool not initialized"}
        return await self.portfolio_tool.get_concentration_metrics()

    # ==================== Market Data Operations ====================

    async def get_quotes(self, instrument_keys: list) -> Dict[str, Any]:
        """Get market quotes for instruments."""
        if not self.market_data_tool:
            return {"status": "error", "message": "Market data tool not initialized"}
        return await self.market_data_tool.get_quotes(instrument_keys)

    async def get_ltp(self, instrument_keys: list) -> Dict[str, Any]:
        """Get last traded price."""
        if not self.market_data_tool:
            return {"status": "error", "message": "Market data tool not initialized"}
        return await self.market_data_tool.get_ltp(instrument_keys)

    async def get_technical_analysis(self, instrument_key: str, period: int = 20) -> Dict[str, Any]:
        """Get technical analysis."""
        if not self.market_data_tool:
            return {"status": "error", "message": "Market data tool not initialized"}
        return await self.market_data_tool.get_technical_analysis(instrument_key, period)

    async def get_option_chain(
        self, instrument_key: str, expiry_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get option chain analysis."""
        if not self.market_data_tool:
            return {"status": "error", "message": "Market data tool not initialized"}
        return await self.market_data_tool.get_option_chain_analysis(instrument_key, expiry_date)

    # ==================== Order Operations ====================

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
        """Place an order."""
        if not self.order_tool:
            return {"status": "error", "message": "Order tool not initialized"}
        return await self.order_tool.place_order(
            instrument_key=instrument_key,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            product_type=product_type,
            validity=validity,
        )

    async def get_open_orders(self) -> Dict[str, Any]:
        """Get all open orders."""
        if not self.order_tool:
            return {"status": "error", "message": "Order tool not initialized"}
        return await self.order_tool.get_open_orders()

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        if not self.order_tool:
            return {"status": "error", "message": "Order tool not initialized"}
        return await self.order_tool.cancel_order(order_id)

    async def create_gtt_order(
        self,
        instrument_key: str,
        quantity: int,
        side: str,
        price: float,
        trigger_price: float,
        product_type: str = "MIS",
    ) -> Dict[str, Any]:
        """Create a Good-Till-Triggered order."""
        if not self.order_tool:
            return {"status": "error", "message": "Order tool not initialized"}
        return await self.order_tool.create_gtt_order(
            instrument_key=instrument_key,
            quantity=quantity,
            side=side,
            price=price,
            trigger_price=trigger_price,
            product_type=product_type,
        )

    # ==================== Risk Operations ====================

    async def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio risk metrics."""
        if not self.risk_tool:
            return {"status": "error", "message": "Risk tool not initialized"}
        return await self.risk_tool.calculate_portfolio_metrics()

    async def identify_risk_exposures(self) -> Dict[str, Any]:
        """Identify risk exposures."""
        if not self.risk_tool:
            return {"status": "error", "message": "Risk tool not initialized"}
        return await self.risk_tool.identify_risk_exposures()

    # ==================== Account Operations ====================

    def get_profile(self) -> Dict[str, Any]:
        """Get user profile information."""
        return self.client.get_profile()

    def get_fund_and_margin(self) -> Dict[str, Any]:
        """Get available funds and margin."""
        return self.client.get_fund_and_margin()

    def get_instruments(self, segment: Optional[str] = None):
        """Get available trading instruments."""
        return self.client.get_instruments(segment)

    def close(self):
        """Close the integration."""
        self.client.close()
        logger.info("Upstox integration closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ==================== Async Context Manager ====================


class AsyncUpstoxIntegration(UpstoxIntegration):
    """Async-compatible version of Upstox integration."""

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()


# ==================== Module Functions ====================


async def create_upstox_integration(
    access_token: str,
    api_key: Optional[str] = None,
    sandbox_mode: bool = True,
    timeout: int = 30,
) -> UpstoxIntegration:
    """
    Create and initialize Upstox integration.

    Args:
        access_token: Upstox OAuth access token
        api_key: Optional API key
        sandbox_mode: Use sandbox environment
        timeout: Request timeout

    Returns:
        Initialized Upstox integration instance
    """
    integration = UpstoxIntegration(
        access_token=access_token,
        api_key=api_key,
        sandbox_mode=sandbox_mode,
        timeout=timeout,
    )

    if await integration.initialize():
        return integration
    else:
        raise RuntimeError("Failed to initialize Upstox integration")


async def register_upstox_tools(integration: UpstoxIntegration, agent_registry: Any) -> bool:
    """
    Register Upstox tools with agent registry.

    Args:
        integration: Upstox integration instance
        agent_registry: Agent registry

    Returns:
        Success status
    """
    return await integration.register_with_agents(agent_registry)


# ==================== Exports ====================

__all__ = [
    "UpstoxIntegration",
    "AsyncUpstoxIntegration",
    "UpstoxClient",
    "UpstoxPortfolioTool",
    "UpstoxMarketDataTool",
    "UpstoxOrderTool",
    "UpstoxRiskAnalysisTool",
    "create_upstox_integration",
    "register_upstox_tools",
]
