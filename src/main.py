"""Main bot application."""

import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from .config import get_settings
from .utils import setup_logging
from .data import BinanceDataClient, WebSocketManager
from .storage import RedisCache, HistoricalStore
from .persistence import Database
from .risk import RiskManager
from .execution import OrderExecutor
from .strategies import GridStrategy, DCAStrategy, TrendFollowingStrategy, SignalType
from .monitoring import TelegramNotifier, MetricsCollector

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(self):
        """Initialize trading bot."""
        self.settings = get_settings()

        # Setup logging
        setup_logging(self.settings.log_level)

        logger.info("Initializing Binance Trading Bot...")

        # Initialize components
        self.data_client = BinanceDataClient()
        self.ws_manager = WebSocketManager(on_message=self.handle_market_data)
        self.redis = RedisCache()
        self.historical_store = HistoricalStore()
        self.db = Database()
        self.risk_manager = RiskManager(redis_cache=self.redis, database=self.db)
        self.executor = OrderExecutor(risk_manager=self.risk_manager, database=self.db)
        self.telegram = TelegramNotifier()
        self.metrics = MetricsCollector()

        # Initialize strategies
        self.strategies = {}
        self._initialize_strategies()

        # State
        self.running = False
        self.last_health_check = datetime.now()

        logger.info("Bot initialization complete")

    def _initialize_strategies(self):
        """Initialize trading strategies."""
        for symbol in self.settings.trading_pairs_list:
            # Example: Initialize Grid strategy for first symbol
            if symbol == self.settings.trading_pairs_list[0]:
                self.strategies[f"grid_{symbol}"] = GridStrategy(
                    symbol=symbol,
                    grid_levels=10,
                    price_range_percent=3.0,
                    position_size_usd=100.0
                )

            # Example: Initialize DCA for all symbols
            self.strategies[f"dca_{symbol}"] = DCAStrategy(
                symbol=symbol,
                purchase_amount_usd=50.0,
                interval_hours=24
            )

        logger.info(f"Initialized {len(self.strategies)} strategies")

    def start(self):
        """Start the trading bot."""
        logger.info("Starting trading bot...")

        # Check database
        self.db.create_tables()

        # Health checks
        if not self._perform_health_checks():
            logger.error("Health checks failed, aborting start")
            return False

        # Sync positions from exchange
        logger.info("Syncing positions from Binance exchange...")
        sync_results = self.executor.sync_positions_from_exchange(
            trading_pairs=self.settings.trading_pairs_list
        )

        # Log sync summary
        if 'error' in sync_results:
            logger.error(f"Position sync failed: {sync_results['error']}")
            self.telegram.alert_error(
                "Position Sync Failed",
                sync_results['error']
            )
        else:
            logger.info(
                f"Position sync complete: "
                f"{sync_results['synced_count']} synced, "
                f"{sync_results['created_count']} created, "
                f"{sync_results['updated_count']} updated, "
                f"{sync_results['closed_count']} closed"
            )

            # Send Telegram notification if there were discrepancies
            if sync_results['discrepancies']:
                self.telegram.send_message(
                    f"⚠️ Position Sync Discrepancies Found:\n\n"
                    f"Found {len(sync_results['discrepancies'])} discrepancies between "
                    f"database and exchange positions.\n\n"
                    f"Details logged. Please review."
                )

        # Start monitoring
        self.metrics.start_server()

        # Subscribe to market data
        self._subscribe_market_data()

        # Start strategies
        for strategy in self.strategies.values():
            strategy.start()

        self.running = True

        # Send startup notification
        self.telegram.alert_system_status(
            "started",
            f"Trading {len(self.settings.trading_pairs_list)} pairs with {len(self.strategies)} strategies"
        )

        logger.info("Trading bot started successfully")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Main loop
        self._run_main_loop()

        return True

    def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")

        self.running = False

        # Stop strategies
        for strategy in self.strategies.values():
            strategy.stop()

        # Stop WebSocket
        self.ws_manager.stop()

        # Send shutdown notification
        self.telegram.alert_system_status("stopped", "Bot shutdown gracefully")

        logger.info("Trading bot stopped")

    def _perform_health_checks(self) -> bool:
        """Perform system health checks.

        Returns:
            True if all checks pass
        """
        logger.info("Performing health checks...")

        # Check Binance API
        if not self.data_client.ping():
            logger.error("Binance API health check failed")
            return False

        # Check Redis
        if not self.redis.health_check():
            logger.error("Redis health check failed")
            return False

        # Check Database
        if not self.db.health_check():
            logger.error("Database health check failed")
            return False

        logger.info("All health checks passed")
        return True

    def _subscribe_market_data(self):
        """Subscribe to market data streams."""
        for symbol in self.settings.trading_pairs_list:
            # Subscribe to ticker for price updates
            self.ws_manager.subscribe_ticker_stream(symbol)

            # Subscribe to klines for strategy data
            self.ws_manager.subscribe_kline_stream(symbol, "1m")

            logger.info(f"Subscribed to market data for {symbol}")

    def handle_market_data(self, data_type: str, data: dict):
        """Handle incoming market data.

        Args:
            data_type: Type of market data (ticker, kline, etc.)
            data: Market data
        """
        try:
            symbol = data.get("symbol")

            if not symbol:
                return

            # Record metric
            self.metrics.record_websocket_message(data_type)

            # Cache data
            if data_type == "ticker":
                self.redis.set_price(symbol, data["price"])
                self.redis.set_ticker(symbol, data)

            elif data_type == "kline":
                if data["is_closed"]:
                    # Save completed kline
                    self._save_kline(symbol, data)

            # Update position risk
            if data_type == "ticker":
                from decimal import Decimal
                self.risk_manager.update_position_risk(symbol, Decimal(str(data["price"])))

        except Exception as e:
            logger.error(f"Error handling market data: {e}")
            self.metrics.record_error("market_data_handler")

    def _save_kline(self, symbol: str, kline_data: dict):
        """Save kline to historical store.

        Args:
            symbol: Trading pair
            kline_data: Kline data
        """
        import pandas as pd

        df = pd.DataFrame([{
            "timestamp": kline_data["timestamp"],
            "open": kline_data["open"],
            "high": kline_data["high"],
            "low": kline_data["low"],
            "close": kline_data["close"],
            "volume": kline_data["volume"]
        }])

        self.historical_store.save_klines(symbol, df)

    def _run_main_loop(self):
        """Run main bot loop."""
        logger.info("Entering main loop...")

        while self.running:
            try:
                # Check circuit breaker
                self.risk_manager.check_daily_loss_circuit_breaker()

                if self.risk_manager.is_circuit_breaker_active():
                    logger.warning("Circuit breaker active, skipping trading")
                    time.sleep(60)
                    continue

                # Process strategies
                self._process_strategies()

                # Periodic health check
                if datetime.now() - self.last_health_check > timedelta(minutes=5):
                    self._perform_health_checks()
                    self.last_health_check = datetime.now()

                # Update metrics
                self._update_metrics()

                # Sleep
                time.sleep(10)  # Run every 10 seconds

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.metrics.record_error("main_loop")
                time.sleep(30)

    def _process_strategies(self):
        """Process all active strategies."""
        for strategy_name, strategy in self.strategies.items():
            if not strategy.is_active:
                continue

            try:
                # Get market data
                symbol = strategy.symbol
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=24)

                df = self.data_client.get_klines(
                    symbol=symbol,
                    interval="1m",
                    start_time=start_time,
                    end_time=end_time,
                    limit=100
                )

                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    continue

                # Generate signal
                signal = strategy.generate_signal(df)

                # Record metric
                self.metrics.record_strategy_signal(strategy.name, signal.signal_type.value)

                # Execute if not HOLD
                if signal.signal_type != SignalType.HOLD:
                    self._execute_signal(signal, strategy_name)

            except Exception as e:
                logger.error(f"Error processing strategy {strategy_name}: {e}")
                self.metrics.record_error("strategy_processing")

    def _execute_signal(self, signal, strategy_name: str):
        """Execute trading signal.

        Args:
            signal: Trading signal
            strategy_name: Strategy name
        """
        logger.info(f"Executing signal from {strategy_name}: {signal.signal_type.value} {signal.symbol}")

        # Place order
        success, order_data, message = self.executor.place_order(
            symbol=signal.symbol,
            side=signal.signal_type.value,
            order_type="LIMIT",
            quantity=signal.quantity,
            price=signal.price,
            strategy_name=strategy_name,
            dry_run=self.settings.binance_testnet  # Use dry run in testnet
        )

        if success:
            logger.info(f"Order placed successfully: {message}")
            self.telegram.alert_order_placed(
                symbol=signal.symbol,
                side=signal.signal_type.value,
                order_type="LIMIT",
                quantity=float(signal.quantity),
                price=float(signal.price)
            )
        else:
            logger.error(f"Order failed: {message}")
            self.telegram.alert_error("Order Failed", message)

    def _update_metrics(self):
        """Update monitoring metrics."""
        try:
            # Update risk metrics
            risk_metrics = self.risk_manager.get_risk_metrics()

            self.metrics.update_total_exposure(float(risk_metrics.total_exposure_usd))
            self.metrics.update_daily_loss(float(risk_metrics.daily_loss_usd))
            self.metrics.update_circuit_breaker(risk_metrics.circuit_breaker_active)

            # Update position metrics
            for symbol in self.settings.trading_pairs_list:
                position = self.db.get_position(symbol)
                if position:
                    from decimal import Decimal
                    value = Decimal(str(position.quantity or 0)) * Decimal(str(position.current_price or 0))
                    self.metrics.update_position(
                        symbol=symbol,
                        is_open=position.is_open,
                        value_usd=float(value)
                    )

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def _signal_handler(self, signum, frame):
        """Handle system signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)


def main():
    """Main entry point."""
    bot = TradingBot()
    bot.start()


if __name__ == "__main__":
    main()
