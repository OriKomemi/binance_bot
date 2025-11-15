"""WebSocket manager for real-time market data streaming."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional
import websockets
from binance import ThreadedWebsocketManager

from ..config import get_settings

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manager for Binance WebSocket streams."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        on_message: Optional[Callable] = None
    ):
        """Initialize WebSocket manager.

        Args:
            api_key: Binance API key (optional)
            api_secret: Binance API secret (optional)
            on_message: Callback function for messages
        """
        settings = get_settings()
        self.api_key = api_key or settings.binance_api_key
        self.api_secret = api_secret or settings.binance_api_secret
        self.testnet = settings.binance_testnet

        self.on_message = on_message
        self.twm: Optional[ThreadedWebsocketManager] = None
        self.active_streams: Dict[str, str] = {}

        logger.info("Initialized WebSocket manager")

    def start(self):
        """Start the WebSocket manager."""
        if self.twm is None:
            self.twm = ThreadedWebsocketManager(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            self.twm.start()
            logger.info("WebSocket manager started")

    def stop(self):
        """Stop the WebSocket manager and all streams."""
        if self.twm:
            self.twm.stop()
            self.twm = None
            self.active_streams.clear()
            logger.info("WebSocket manager stopped")

    def subscribe_trade_stream(self, symbol: str, callback: Optional[Callable] = None) -> str:
        """Subscribe to trade stream for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            callback: Custom callback function (uses default if None)

        Returns:
            Stream key for managing the subscription
        """
        if not self.twm:
            self.start()

        symbol_lower = symbol.lower()
        handler = callback or self._default_trade_handler

        stream_key = self.twm.start_trade_socket(
            callback=handler,
            symbol=symbol_lower
        )

        self.active_streams[f"trade_{symbol}"] = stream_key
        logger.info(f"Subscribed to trade stream for {symbol}")
        return stream_key

    def subscribe_kline_stream(
        self,
        symbol: str,
        interval: str,
        callback: Optional[Callable] = None
    ) -> str:
        """Subscribe to kline (candlestick) stream.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            callback: Custom callback function

        Returns:
            Stream key
        """
        if not self.twm:
            self.start()

        symbol_lower = symbol.lower()
        handler = callback or self._default_kline_handler

        stream_key = self.twm.start_kline_socket(
            callback=handler,
            symbol=symbol_lower,
            interval=interval
        )

        self.active_streams[f"kline_{symbol}_{interval}"] = stream_key
        logger.info(f"Subscribed to kline stream for {symbol} ({interval})")
        return stream_key

    def subscribe_ticker_stream(self, symbol: str, callback: Optional[Callable] = None) -> str:
        """Subscribe to ticker stream.

        Args:
            symbol: Trading pair symbol
            callback: Custom callback function

        Returns:
            Stream key
        """
        if not self.twm:
            self.start()

        symbol_lower = symbol.lower()
        handler = callback or self._default_ticker_handler

        stream_key = self.twm.start_symbol_ticker_socket(
            callback=handler,
            symbol=symbol_lower
        )

        self.active_streams[f"ticker_{symbol}"] = stream_key
        logger.info(f"Subscribed to ticker stream for {symbol}")
        return stream_key

    def subscribe_depth_stream(
        self,
        symbol: str,
        depth: str = "20",
        callback: Optional[Callable] = None
    ) -> str:
        """Subscribe to order book depth stream.

        Args:
            symbol: Trading pair symbol
            depth: Depth level (5, 10, 20)
            callback: Custom callback function

        Returns:
            Stream key
        """
        if not self.twm:
            self.start()

        symbol_lower = symbol.lower()
        handler = callback or self._default_depth_handler

        stream_key = self.twm.start_depth_socket(
            callback=handler,
            symbol=symbol_lower,
            depth=depth
        )

        self.active_streams[f"depth_{symbol}_{depth}"] = stream_key
        logger.info(f"Subscribed to depth stream for {symbol} (depth={depth})")
        return stream_key

    def subscribe_user_stream(self, callback: Optional[Callable] = None) -> str:
        """Subscribe to user data stream for account updates.

        Args:
            callback: Custom callback function

        Returns:
            Stream key
        """
        if not self.twm:
            self.start()

        handler = callback or self._default_user_handler

        stream_key = self.twm.start_user_socket(callback=handler)

        self.active_streams["user_data"] = stream_key
        logger.info("Subscribed to user data stream")
        return stream_key

    def unsubscribe(self, stream_name: str):
        """Unsubscribe from a specific stream.

        Args:
            stream_name: Name of the stream (e.g., 'trade_BTCUSDT')
        """
        if stream_name in self.active_streams:
            stream_key = self.active_streams[stream_name]
            if self.twm:
                self.twm.stop_socket(stream_key)
            del self.active_streams[stream_name]
            logger.info(f"Unsubscribed from {stream_name}")

    def _default_trade_handler(self, msg: Dict):
        """Default handler for trade messages."""
        if msg["e"] == "error":
            logger.error(f"Trade stream error: {msg}")
            return

        trade_data = {
            "symbol": msg["s"],
            "price": float(msg["p"]),
            "quantity": float(msg["q"]),
            "timestamp": datetime.fromtimestamp(msg["T"] / 1000),
            "is_buyer_maker": msg["m"],
            "trade_id": msg["t"]
        }

        logger.debug(f"Trade: {trade_data['symbol']} @ {trade_data['price']}")

        if self.on_message:
            self.on_message("trade", trade_data)

    def _default_kline_handler(self, msg: Dict):
        """Default handler for kline messages."""
        if msg["e"] == "error":
            logger.error(f"Kline stream error: {msg}")
            return

        kline = msg["k"]
        kline_data = {
            "symbol": msg["s"],
            "interval": kline["i"],
            "timestamp": datetime.fromtimestamp(kline["t"] / 1000),
            "open": float(kline["o"]),
            "high": float(kline["h"]),
            "low": float(kline["l"]),
            "close": float(kline["c"]),
            "volume": float(kline["v"]),
            "is_closed": kline["x"],
            "quote_volume": float(kline["q"]),
            "trades": kline["n"]
        }

        if self.on_message:
            self.on_message("kline", kline_data)

    def _default_ticker_handler(self, msg: Dict):
        """Default handler for ticker messages."""
        if msg["e"] == "error":
            logger.error(f"Ticker stream error: {msg}")
            return

        ticker_data = {
            "symbol": msg["s"],
            "price": float(msg["c"]),
            "price_change": float(msg["p"]),
            "price_change_percent": float(msg["P"]),
            "high": float(msg["h"]),
            "low": float(msg["l"]),
            "volume": float(msg["v"]),
            "timestamp": datetime.fromtimestamp(msg["E"] / 1000)
        }

        if self.on_message:
            self.on_message("ticker", ticker_data)

    def _default_depth_handler(self, msg: Dict):
        """Default handler for depth messages."""
        if msg["e"] == "error":
            logger.error(f"Depth stream error: {msg}")
            return

        depth_data = {
            "symbol": msg.get("s", ""),
            "bids": [[float(price), float(qty)] for price, qty in msg.get("bids", [])],
            "asks": [[float(price), float(qty)] for price, qty in msg.get("asks", [])],
            "timestamp": datetime.now()
        }

        if self.on_message:
            self.on_message("depth", depth_data)

    def _default_user_handler(self, msg: Dict):
        """Default handler for user data messages."""
        if msg["e"] == "error":
            logger.error(f"User stream error: {msg}")
            return

        event_type = msg.get("e")

        if event_type == "outboundAccountPosition":
            # Account update
            logger.info(f"Account update received: {len(msg.get('B', []))} balances")
        elif event_type == "executionReport":
            # Order update
            order_data = {
                "symbol": msg["s"],
                "order_id": msg["i"],
                "client_order_id": msg["c"],
                "side": msg["S"],
                "order_type": msg["o"],
                "status": msg["X"],
                "price": float(msg["p"]),
                "quantity": float(msg["q"]),
                "executed_qty": float(msg["z"]),
                "timestamp": datetime.fromtimestamp(msg["T"] / 1000)
            }
            logger.info(f"Order update: {order_data}")

        if self.on_message:
            self.on_message("user", msg)
