"""Binance client with Ed25519 authentication support."""

import logging
import time
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .ed25519_auth import Ed25519Authenticator

logger = logging.getLogger(__name__)


class BinanceEd25519Client:
    """Binance API client with Ed25519 authentication."""

    def __init__(
        self,
        api_key: str,
        private_key_path: str,
        testnet: bool = True,
        password: Optional[str] = None
    ):
        """Initialize Binance Ed25519 client.

        Args:
            api_key: Binance API key
            private_key_path: Path to Ed25519 private key PEM file
            testnet: Use testnet (default: True)
            password: Password for encrypted private key (optional)
        """
        self.api_key = api_key
        self.testnet = testnet

        # Setup base URL
        if testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"

        # Initialize authenticator
        self.auth = Ed25519Authenticator(api_key, private_key_path, password)

        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Ed25519 client initialized (testnet={testnet})")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict:
        """Make API request.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request needs to be signed

        Returns:
            Response JSON
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        # Sign request if required
        if signed:
            params = self.auth.sign_request(params)
            headers = self.auth.get_headers()
        else:
            headers = {}

        # Make request
        response = self.session.request(
            method=method,
            url=url,
            params=params if method == 'GET' else None,
            data=params if method != 'GET' else None,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        return response.json()

    def ping(self) -> bool:
        """Test connectivity.

        Returns:
            True if successful
        """
        try:
            self._request('GET', '/api/v3/ping')
            return True
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False

    def get_server_time(self) -> int:
        """Get server time.

        Returns:
            Server timestamp in milliseconds
        """
        response = self._request('GET', '/api/v3/time')
        return response['serverTime']

    def get_account(self) -> Dict:
        """Get account information.

        Returns:
            Account information
        """
        return self._request('GET', '/api/v3/account', signed=True)

    def get_ticker_price(self, symbol: str) -> Dict:
        """Get ticker price.

        Args:
            symbol: Trading pair symbol

        Returns:
            Ticker price information
        """
        params = {'symbol': symbol}
        return self._request('GET', '/api/v3/ticker/price', params=params)

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = 'GTC',
        **kwargs
    ) -> Dict:
        """Create a new order.

        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            order_type: Order type (LIMIT/MARKET/etc)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            time_in_force: Time in force (GTC/IOC/FOK)
            **kwargs: Additional parameters

        Returns:
            Order response
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': f'{quantity:.8f}',
        }

        if order_type == 'LIMIT':
            if price is None:
                raise ValueError("Price is required for LIMIT orders")
            params['price'] = f'{price:.8f}'
            params['timeInForce'] = time_in_force

        # Add any additional parameters
        params.update(kwargs)

        return self._request('POST', '/api/v3/order', params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: Optional[int] = None,
                     orig_client_order_id: Optional[str] = None) -> Dict:
        """Cancel an order.

        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            orig_client_order_id: Original client order ID

        Returns:
            Cancellation response
        """
        params = {'symbol': symbol}

        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        else:
            raise ValueError("Either order_id or orig_client_order_id must be provided")

        return self._request('DELETE', '/api/v3/order', params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict:
        """Get order status.

        Args:
            symbol: Trading pair symbol
            order_id: Order ID

        Returns:
            Order information
        """
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._request('GET', '/api/v3/order', params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get open orders.

        Args:
            symbol: Trading pair symbol (optional, gets all if not specified)

        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params['symbol'] = symbol

        return self._request('GET', '/api/v3/openOrders', params=params, signed=True)

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> list:
        """Get kline/candlestick data.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 5m, 1h, 1d, etc.)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of klines (max 1000)

        Returns:
            List of klines
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1000)
        }

        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        return self._request('GET', '/api/v3/klines', params=params)
