"""Binance REST API client for data fetching."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


class BinanceDataClient:
    """Client for fetching data from Binance REST API."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize Binance client.

        Args:
            api_key: Binance API key (optional, uses settings if not provided)
            api_secret: Binance API secret (optional, uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.binance_api_key
        self.api_secret = api_secret or settings.binance_api_secret
        self.testnet = settings.binance_testnet

        # Initialize Binance client
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet
        )

        logger.info(f"Initialized Binance client (testnet={self.testnet})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_server_time(self) -> int:
        """Get Binance server time.

        Returns:
            Server timestamp in milliseconds
        """
        return self.client.get_server_time()["serverTime"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict:
        """Get exchange information.

        Args:
            symbol: Specific symbol to get info for (optional)

        Returns:
            Exchange information dictionary
        """
        if symbol:
            return self.client.get_symbol_info(symbol)
        return self.client.get_exchange_info()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_ticker_price(self, symbol: str) -> Dict:
        """Get current ticker price.

        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)

        Returns:
            Ticker price information
        """
        return self.client.get_symbol_ticker(symbol=symbol)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book depth.

        Args:
            symbol: Trading pair symbol
            limit: Depth limit (5, 10, 20, 50, 100, 500, 1000, 5000)

        Returns:
            Order book data
        """
        return self.client.get_order_book(symbol=symbol, limit=limit)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> pd.DataFrame:
        """Get historical klines (candlestick data).

        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            start_time: Start time for historical data
            end_time: End time for historical data
            limit: Number of klines to fetch (max 1000)

        Returns:
            DataFrame with OHLCV data
        """
        # Prepare parameters
        params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        # Fetch klines
        klines = self.client.get_klines(**params)

        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ])

        # Convert types
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

        numeric_columns = ["open", "high", "low", "close", "volume",
                          "quote_asset_volume", "taker_buy_base_asset_volume",
                          "taker_buy_quote_asset_volume"]
        df[numeric_columns] = df[numeric_columns].astype(float)
        df["number_of_trades"] = df["number_of_trades"].astype(int)

        # Drop unnecessary columns
        df = df.drop(["ignore"], axis=1)

        logger.debug(f"Fetched {len(df)} klines for {symbol} ({interval})")
        return df

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get recent trades.

        Args:
            symbol: Trading pair symbol
            limit: Number of trades to fetch (max 1000)

        Returns:
            List of recent trades
        """
        return self.client.get_recent_trades(symbol=symbol, limit=min(limit, 1000))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_24h_ticker(self, symbol: str) -> Dict:
        """Get 24-hour price change statistics.

        Args:
            symbol: Trading pair symbol

        Returns:
            24h ticker statistics
        """
        return self.client.get_ticker(symbol=symbol)

    def get_account_info(self) -> Dict:
        """Get account information.

        Returns:
            Account information including balances
        """
        return self.client.get_account()

    def get_asset_balance(self, asset: str) -> Optional[Dict]:
        """Get balance for a specific asset.

        Args:
            asset: Asset symbol (e.g., BTC, USDT)

        Returns:
            Asset balance information
        """
        return self.client.get_asset_balance(asset=asset)

    def ping(self) -> bool:
        """Test connectivity to Binance API.

        Returns:
            True if connection successful
        """
        try:
            self.client.ping()
            return True
        except BinanceAPIException as e:
            logger.error(f"Binance API ping failed: {e}")
            return False
