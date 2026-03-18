"""
Upstox API Client

Comprehensive API client for Upstox trading platform integration.
Handles authentication, market data, portfolio management, and order execution.

API Documentation: https://upstox.com/api
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import requests

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported by Upstox"""

    REGULAR = "REGULAR"
    MARGIN = "MARGIN"
    COVER = "COVER"


class OrderAction(Enum):
    """Order actions"""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status values"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially filled"
    EXPIRED = "expired"


class UpstoxAuthError(Exception):
    """Raised when authentication fails"""

    pass


class UpstoxAPIError(Exception):
    """Raised when API request fails"""

    pass


class UpstoxClient:
    """
    Upstox API Client

    Provides access to trading account data, market information, and order management.
    Supports both synchronous and asynchronous operations.

    Attributes:
        api_key: Upstox API key
        access_token: OAuth access token
        base_url: API base URL (default: https://api.upstox.com/v2)
        sandbox_mode: If True, use sandbox endpoints
    """

    BASE_URL = "https://api.upstox.com/v2"
    SANDBOX_URL = "https://sandbox.upstox.com/v2"
    HISTORICAL_DATA_URL = "https://api.upstox.com/v3"

    # Rate limits
    RATE_LIMIT = 100  # requests per minute
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(
        self, api_key: str, access_token: str, sandbox_mode: bool = False, timeout: int = 30
    ):
        """
        Initialize Upstox API Client

        Args:
            api_key: Upstox API key
            access_token: OAuth 2.0 access token
            sandbox_mode: Use sandbox environment
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = self.SANDBOX_URL if sandbox_mode else self.BASE_URL
        self.sandbox_mode = sandbox_mode
        self.timeout = timeout
        self._request_count = 0
        self._rate_limit_reset = datetime.now()

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = datetime.now()
        if (now - self._rate_limit_reset).total_seconds() > self.RATE_LIMIT_WINDOW:
            self._request_count = 0
            self._rate_limit_reset = now

        if self._request_count >= self.RATE_LIMIT:
            wait_time = self.RATE_LIMIT_WINDOW - (now - self._rate_limit_reset).total_seconds()
            logger.warning(f"Rate limit approaching, waiting {wait_time:.1f}s")
            asyncio.sleep(wait_time)
            self._request_count = 0
            self._rate_limit_reset = datetime.now()

        self._request_count += 1

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Upstox API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            base_url: Override base URL

        Returns:
            API response as dictionary

        Raises:
            UpstoxAPIError: If request fails
        """
        self._check_rate_limit()

        url = f"{base_url or self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method, url=url, params=params, json=data, timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            if result.get("status") != "success":
                raise UpstoxAPIError(
                    f"API error: {result.get('errors', result.get('message', 'Unknown error'))}"
                )

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise UpstoxAPIError(f"Request failed: {str(e)}")

    # ==================== Authentication ====================

    def verify_token(self) -> bool:
        """
        Verify if access token is valid

        Returns:
            True if token is valid
        """
        try:
            self.get_profile()
            return True
        except (UpstoxAPIError, UpstoxAuthError):
            return False

    # ==================== User Profile ====================

    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information

        Returns:
            User profile data including email, name, account status
        """
        return self._make_request("GET", "/user/profile")

    def get_fund_and_margin(self) -> Dict[str, Any]:
        """
        Get available funds and margin information

        Returns:
            Fund and margin details
            {
                "available_margin": float,
                "used_margin": float,
                "opening_balance": float,
                "equity": float,
                "cash_margin": float,
                "adhoc_margin": float
            }
        """
        return self._make_request("GET", "/user/get-funds-and-margin")

    # ==================== Instruments ====================

    def get_instruments(self, segment: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available instruments (stocks, futures, options)

        Args:
            segment: Filter by segment (NSE_EQ, NSE_FO, BSE_EQ, etc.)

        Returns:
            List of available instruments
        """
        # Instruments are served as static JSON files
        if segment:
            url = f"https://assets.upstox.com/market-data-feed/instruments/{segment}.json"
        else:
            url = "https://assets.upstox.com/market-data-feed/instruments/complete.json"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch instruments: {e}")
            return []

    def search_instruments(self, query: str, segment: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for instruments by name or symbol

        Args:
            query: Search query (symbol or name)
            segment: Filter by segment

        Returns:
            List of matching instruments
        """
        instruments = self.get_instruments(segment)
        query_lower = query.lower()

        return [
            inst
            for inst in instruments
            if query_lower in inst.get("trading_symbol", "").lower()
            or query_lower in inst.get("name", "").lower()
        ]

    # ==================== Market Data ====================

    def get_market_quote(self, instrument_keys: List[str]) -> Dict[str, Any]:
        """
        Get real-time market quotes for instruments

        Args:
            instrument_keys: List of instrument keys (e.g., ['NSE_EQ|INE002A01018'])

        Returns:
            Market quote data including price, volume, OI
        """
        params = {"mode": "full", "instrument_key": ",".join(instrument_keys)}
        return self._make_request("GET", "/market-quote/", params=params)

    def get_ltp(self, instrument_keys: List[str]) -> Dict[str, float]:
        """
        Get Last Traded Price (LTP) for instruments

        Args:
            instrument_keys: List of instrument keys

        Returns:
            Dictionary mapping instrument_key to LTP
        """
        params = {"mode": "ltp", "instrument_key": ",".join(instrument_keys)}
        response = self._make_request("GET", "/market-quote/", params=params)

        result = {}
        for key, data in response.get("data", {}).items():
            if isinstance(data, dict):
                result[key] = data.get("ltp", 0)

        return result

    def get_historical_data(
        self,
        instrument_key: str,
        unit: str = "days",
        interval: int = 1,
        to_date: str = None,
        from_date: str = None,
    ) -> List[List[Any]]:
        """
        Get historical OHLC data (V3 API)

        Args:
            instrument_key: Instrument key (e.g., 'NSE_EQ|INE002A01018')
            unit: Time unit ('minutes', 'hours', 'days', 'weeks', 'months')
            interval: Interval value
            to_date: End date (YYYY-MM-DD)
            from_date: Start date (YYYY-MM-DD)

        Returns:
            List of OHLC candles
            [[timestamp, open, high, low, close, volume, oi], ...]
        """
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        endpoint = f"/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
        response = self._make_request("GET", endpoint, base_url=self.HISTORICAL_DATA_URL)

        return response.get("data", {}).get("candles", [])

    def get_intraday_data(
        self, instrument_key: str, unit: str = "minutes", interval: int = 5, to_date: str = None
    ) -> List[List[Any]]:
        """
        Get intraday OHLC data for today

        Args:
            instrument_key: Instrument key
            unit: Time unit ('minutes', 'hours')
            interval: Interval value
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of OHLC candles
        """
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")

        endpoint = f"/intraday-candle/{instrument_key}/{unit}/{interval}/{to_date}"
        response = self._make_request("GET", endpoint, base_url=self.HISTORICAL_DATA_URL)

        return response.get("data", {}).get("candles", [])

    def get_option_chain(
        self, instrument_key: str, expiry_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get option chain for an underlying symbol

        Args:
            instrument_key: Underlying instrument key (e.g., 'NSE_INDEX|Nifty 50')
            expiry_date: Specific expiry date (YYYY-MM-DD)

        Returns:
            List of option contracts
        """
        params = {"instrument_key": instrument_key}
        if expiry_date:
            params["expiry_date"] = expiry_date

        return self._make_request("GET", "/option/contract", params=params)

    # ==================== Portfolio ====================

    def get_portfolio(self) -> Dict[str, Any]:
        """
        Get portfolio holdings

        Returns:
            Portfolio data with all holdings
        """
        return self._make_request("GET", "/portfolio/long-term-holdings")

    def get_positions(self) -> Dict[str, Any]:
        """
        Get open positions (intraday and carry forward)

        Returns:
            List of open positions with P&L
        """
        return self._make_request("GET", "/portfolio/short-term-holdings")

    def get_profit_and_loss(self) -> Dict[str, Any]:
        """
        Get trade profit and loss

        Returns:
            P&L data including realized and unrealized P&L
        """
        return self._make_request("GET", "/portfolio/trade-profit-loss")

    # ==================== Orders ====================

    def place_order(
        self,
        instrument_key: str,
        quantity: int,
        side: str = "BUY",
        order_type: str = "REGULAR",
        price: float = 0,
        product_type: str = "MIS",
        validity: str = "DAY",
        disclosed_quantity: int = 0,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a new order

        Args:
            instrument_key: Instrument key
            quantity: Order quantity
            side: BUY or SELL
            order_type: REGULAR, LIMIT, MARKET
            price: Price for limit orders
            product_type: MIS, CNC, NRML (margin types)
            validity: DAY, IOC, TTL
            disclosed_quantity: Partial disclosure quantity
            tag: Order tag for tracking

        Returns:
            Order response with order_id
        """
        payload = {
            "quantity": quantity,
            "side": side,
            "order_type": order_type,
            "product_type": product_type,
            "validity": validity,
            "instrument_key": instrument_key,
        }

        if price > 0:
            payload["price"] = price
        if disclosed_quantity > 0:
            payload["disclosed_quantity"] = disclosed_quantity
        if tag:
            payload["tag"] = tag

        if self.sandbox_mode:
            return self._make_request("POST", "/order/place", data=payload)
        else:
            logger.warning("Live order placement requires explicit confirmation")
            return {"status": "warning", "message": "Use place_order_live for live trading"}

    def place_order_live(
        self,
        instrument_key: str,
        quantity: int,
        side: str = "BUY",
        order_type: str = "REGULAR",
        price: float = 0,
        product_type: str = "MIS",
        validity: str = "DAY",
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place order on live account (requires explicit call)

        CAUTION: This places actual live orders
        """
        if not self.sandbox_mode:
            logger.warning(f"Placing LIVE order: {side} {quantity} {instrument_key} @ {price}")

        return self.place_order(
            instrument_key=instrument_key,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            product_type=product_type,
            validity=validity,
            tag=tag,
        )

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        disclosed_quantity: Optional[int] = None,
        validity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Modify an existing order

        Args:
            order_id: Order ID to modify
            quantity: New quantity
            price: New price
            order_type: New order type
            disclosed_quantity: New disclosed quantity
            validity: New validity

        Returns:
            Modified order response
        """
        payload = {"order_id": order_id}

        if quantity is not None:
            payload["quantity"] = quantity
        if price is not None:
            payload["price"] = price
        if order_type:
            payload["order_type"] = order_type
        if disclosed_quantity is not None:
            payload["disclosed_quantity"] = disclosed_quantity
        if validity:
            payload["validity"] = validity

        return self._make_request("PUT", "/order/modify", data=payload)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an open order

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation response
        """
        return self._make_request("DELETE", f"/order/cancel/{order_id}")

    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders for the day

        Returns:
            List of orders with status and details
        """
        response = self._make_request("GET", "/order/retrieve-all")
        return response.get("data", [])

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get details of a specific order

        Args:
            order_id: Order ID

        Returns:
            Order details
        """
        response = self._make_request("GET", f"/order/retrieve/{order_id}")
        return response.get("data", {})

    # ==================== GTT Orders ====================

    def create_gtt_order(
        self,
        instrument_key: str,
        quantity: int,
        side: str,
        price: float,
        trigger_price: float,
        product_type: str = "MIS",
        validity: str = "DAY",
    ) -> Dict[str, Any]:
        """
        Create Good Till Triggered (GTT) order

        Args:
            instrument_key: Instrument key
            quantity: Order quantity
            side: BUY or SELL
            price: Order price
            trigger_price: Price to trigger order
            product_type: MIS, CNC, NRML
            validity: DAY, TTL

        Returns:
            GTT order response
        """
        payload = {
            "instrument_key": instrument_key,
            "quantity": quantity,
            "side": side,
            "price": price,
            "trigger_price": trigger_price,
            "product_type": product_type,
            "validity": validity,
        }

        return self._make_request("POST", "/gtt/create", data=payload)

    def get_gtt_orders(self) -> List[Dict[str, Any]]:
        """Get all GTT orders"""
        response = self._make_request("GET", "/gtt/retrieve-all")
        return response.get("data", [])

    def cancel_gtt_order(self, gtt_id: str) -> Dict[str, Any]:
        """Cancel a GTT order"""
        return self._make_request("DELETE", f"/gtt/cancel/{gtt_id}")

    # ==================== Websocket ====================

    def get_websocket_config(self) -> Dict[str, str]:
        """
        Get WebSocket connection details for real-time data

        Returns:
            WebSocket URL and auth token
        """
        response = self._make_request("GET", "/websocket")
        return response.get("data", {})

    # ==================== Cleanup ====================

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
