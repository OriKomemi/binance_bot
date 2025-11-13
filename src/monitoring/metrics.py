"""Prometheus metrics collection."""

import logging
from typing import Optional
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server
)

from ..config import get_settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Prometheus metrics collector."""

    def __init__(self, port: Optional[int] = None):
        """Initialize metrics collector.

        Args:
            port: Prometheus metrics port (uses settings if None)
        """
        settings = get_settings()
        self.port = port or settings.prometheus_port

        # Order metrics
        self.orders_total = Counter(
            "binance_bot_orders_total",
            "Total number of orders placed",
            ["symbol", "side", "status"]
        )

        self.orders_value_usd = Counter(
            "binance_bot_orders_value_usd_total",
            "Total value of orders in USD",
            ["symbol", "side"]
        )

        # Trade metrics
        self.trades_total = Counter(
            "binance_bot_trades_total",
            "Total number of trades executed",
            ["symbol", "side"]
        )

        self.trade_pnl = Histogram(
            "binance_bot_trade_pnl",
            "Trade profit/loss distribution",
            ["symbol"],
            buckets=[-1000, -500, -100, -50, -10, 0, 10, 50, 100, 500, 1000]
        )

        # Position metrics
        self.positions_open = Gauge(
            "binance_bot_positions_open",
            "Number of open positions",
            ["symbol"]
        )

        self.position_value_usd = Gauge(
            "binance_bot_position_value_usd",
            "Position value in USD",
            ["symbol"]
        )

        self.total_exposure_usd = Gauge(
            "binance_bot_total_exposure_usd",
            "Total exposure in USD"
        )

        # PnL metrics
        self.pnl_total = Gauge(
            "binance_bot_pnl_total",
            "Total profit/loss",
            ["symbol"]
        )

        self.pnl_daily = Gauge(
            "binance_bot_pnl_daily",
            "Daily profit/loss"
        )

        # Risk metrics
        self.circuit_breaker_active = Gauge(
            "binance_bot_circuit_breaker_active",
            "Circuit breaker status (1=active, 0=inactive)"
        )

        self.daily_loss = Gauge(
            "binance_bot_daily_loss_usd",
            "Daily loss in USD"
        )

        # System metrics
        self.api_requests_total = Counter(
            "binance_bot_api_requests_total",
            "Total API requests",
            ["endpoint", "status"]
        )

        self.api_request_duration = Histogram(
            "binance_bot_api_request_duration_seconds",
            "API request duration",
            ["endpoint"]
        )

        self.websocket_messages = Counter(
            "binance_bot_websocket_messages_total",
            "WebSocket messages received",
            ["stream_type"]
        )

        self.errors_total = Counter(
            "binance_bot_errors_total",
            "Total errors encountered",
            ["error_type"]
        )

        # Strategy metrics
        self.strategy_signals = Counter(
            "binance_bot_strategy_signals_total",
            "Strategy signals generated",
            ["strategy", "signal_type"]
        )

        logger.info(f"Metrics collector initialized on port {self.port}")

    def start_server(self):
        """Start Prometheus metrics HTTP server."""
        try:
            start_http_server(self.port)
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    # Order tracking
    def record_order_placed(self, symbol: str, side: str, value_usd: float):
        """Record order placement.

        Args:
            symbol: Trading pair
            side: Order side
            value_usd: Order value in USD
        """
        self.orders_total.labels(symbol=symbol, side=side, status="placed").inc()
        self.orders_value_usd.labels(symbol=symbol, side=side).inc(value_usd)

    def record_order_filled(self, symbol: str, side: str):
        """Record order fill.

        Args:
            symbol: Trading pair
            side: Order side
        """
        self.orders_total.labels(symbol=symbol, side=side, status="filled").inc()

    def record_order_cancelled(self, symbol: str, side: str):
        """Record order cancellation.

        Args:
            symbol: Trading pair
            side: Order side
        """
        self.orders_total.labels(symbol=symbol, side=side, status="cancelled").inc()

    # Trade tracking
    def record_trade(self, symbol: str, side: str, pnl: float):
        """Record trade execution.

        Args:
            symbol: Trading pair
            side: Trade side
            pnl: Profit/loss
        """
        self.trades_total.labels(symbol=symbol, side=side).inc()
        self.trade_pnl.labels(symbol=symbol).observe(pnl)

    # Position tracking
    def update_position(self, symbol: str, is_open: bool, value_usd: float):
        """Update position metrics.

        Args:
            symbol: Trading pair
            is_open: Whether position is open
            value_usd: Position value
        """
        self.positions_open.labels(symbol=symbol).set(1 if is_open else 0)
        self.position_value_usd.labels(symbol=symbol).set(value_usd)

    def update_total_exposure(self, exposure_usd: float):
        """Update total exposure.

        Args:
            exposure_usd: Total exposure in USD
        """
        self.total_exposure_usd.set(exposure_usd)

    # PnL tracking
    def update_pnl(self, symbol: str, total_pnl: float):
        """Update PnL metrics.

        Args:
            symbol: Trading pair
            total_pnl: Total PnL
        """
        self.pnl_total.labels(symbol=symbol).set(total_pnl)

    def update_daily_pnl(self, daily_pnl: float):
        """Update daily PnL.

        Args:
            daily_pnl: Daily PnL
        """
        self.pnl_daily.set(daily_pnl)

    # Risk tracking
    def update_circuit_breaker(self, is_active: bool):
        """Update circuit breaker status.

        Args:
            is_active: Whether circuit breaker is active
        """
        self.circuit_breaker_active.set(1 if is_active else 0)

    def update_daily_loss(self, loss_usd: float):
        """Update daily loss.

        Args:
            loss_usd: Daily loss in USD
        """
        self.daily_loss.set(loss_usd)

    # System tracking
    def record_api_request(self, endpoint: str, status: str, duration: float):
        """Record API request.

        Args:
            endpoint: API endpoint
            status: Request status (success/error)
            duration: Request duration in seconds
        """
        self.api_requests_total.labels(endpoint=endpoint, status=status).inc()
        self.api_request_duration.labels(endpoint=endpoint).observe(duration)

    def record_websocket_message(self, stream_type: str):
        """Record WebSocket message.

        Args:
            stream_type: Stream type (trade, kline, etc.)
        """
        self.websocket_messages.labels(stream_type=stream_type).inc()

    def record_error(self, error_type: str):
        """Record error.

        Args:
            error_type: Type of error
        """
        self.errors_total.labels(error_type=error_type).inc()

    # Strategy tracking
    def record_strategy_signal(self, strategy: str, signal_type: str):
        """Record strategy signal.

        Args:
            strategy: Strategy name
            signal_type: Signal type (BUY/SELL/HOLD)
        """
        self.strategy_signals.labels(strategy=strategy, signal_type=signal_type).inc()
