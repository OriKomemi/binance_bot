"""Dry run testing script - Test bot without real trading."""

import sys
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.utils import setup_logging
from src.data import BinanceDataClient
from src.strategies import GridStrategy, DCAStrategy, TrendFollowingStrategy


class DryRunTester:
    """Dry run tester for validating bot functionality."""

    def __init__(self, duration_seconds: int = 300):
        """Initialize dry run tester.

        Args:
            duration_seconds: How long to run the test (default 5 minutes)
        """
        self.duration = duration_seconds
        self.settings = get_settings()
        self.running = True

        # Setup logging
        setup_logging(self.settings.log_level)

        print("=" * 70)
        print("🧪 DRY RUN MODE - NO REAL TRADES WILL BE EXECUTED")
        print("=" * 70)
        print(f"Duration: {duration_seconds} seconds ({duration_seconds/60:.1f} minutes)")
        print(f"Trading pairs: {self.settings.trading_pairs_list}")
        print(f"Testnet mode: {self.settings.binance_testnet}")
        print("=" * 70 + "\n")

        # Initialize components
        self.data_client = BinanceDataClient()
        self.strategies = self._initialize_strategies()

        # Statistics
        self.stats = {
            "signals_generated": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "hold_signals": 0,
            "api_calls": 0,
            "errors": 0
        }

    def _initialize_strategies(self):
        """Initialize test strategies."""
        strategies = {}

        for symbol in self.settings.trading_pairs_list:
            # Test DCA strategy for all pairs
            strategies[f"dca_{symbol}"] = DCAStrategy(
                symbol=symbol,
                purchase_amount_usd=50.0,
                interval_hours=1  # Faster for testing
            )

            # Test Grid strategy for first pair
            if symbol == self.settings.trading_pairs_list[0]:
                strategies[f"grid_{symbol}"] = GridStrategy(
                    symbol=symbol,
                    grid_levels=5,
                    price_range_percent=2.0,
                    position_size_usd=100.0
                )

        print(f"✅ Initialized {len(strategies)} strategies\n")
        return strategies

    def test_api_connectivity(self):
        """Test Binance API connectivity."""
        print("🔍 Testing API connectivity...")

        try:
            # Test ping
            if self.data_client.ping():
                print("✅ API ping successful")

            # Get server time
            server_time = self.data_client.get_server_time()
            print(f"✅ Server time: {datetime.fromtimestamp(server_time/1000)}")

            # Test market data for each pair
            for symbol in self.settings.trading_pairs_list:
                try:
                    ticker = self.data_client.get_ticker_price(symbol)
                    print(f"✅ {symbol}: ${ticker['price']}")
                    self.stats["api_calls"] += 1
                except Exception as e:
                    print(f"❌ Failed to get {symbol} price: {e}")
                    self.stats["errors"] += 1

            print()
            return True

        except Exception as e:
            print(f"❌ API connectivity test failed: {e}\n")
            return False

    def test_data_retrieval(self):
        """Test historical data retrieval."""
        print("🔍 Testing data retrieval...")

        symbol = self.settings.trading_pairs_list[0]

        try:
            # Get recent klines
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)

            df = self.data_client.get_klines(
                symbol=symbol,
                interval="1m",
                start_time=start_time,
                end_time=end_time,
                limit=60
            )

            self.stats["api_calls"] += 1

            if not df.empty:
                print(f"✅ Retrieved {len(df)} klines for {symbol}")
                print(f"   Latest price: ${df.iloc[-1]['close']:.2f}")
                print(f"   Time range: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
            else:
                print(f"⚠️  No data retrieved for {symbol}")

            print()
            return True

        except Exception as e:
            print(f"❌ Data retrieval failed: {e}\n")
            self.stats["errors"] += 1
            return False

    def test_strategy_signals(self):
        """Test strategy signal generation."""
        print("🔍 Testing strategy signal generation...")

        for strategy_name, strategy in self.strategies.items():
            try:
                symbol = strategy.symbol

                # Get market data
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=24)

                df = self.data_client.get_klines(
                    symbol=symbol,
                    interval="1m",
                    start_time=start_time,
                    end_time=end_time,
                    limit=100
                )

                self.stats["api_calls"] += 1

                if df.empty:
                    print(f"⚠️  No data for {strategy_name}")
                    continue

                # Generate signal
                strategy.start()
                signal = strategy.generate_signal(df)

                self.stats["signals_generated"] += 1

                if signal.signal_type.value == "BUY":
                    self.stats["buy_signals"] += 1
                    icon = "🟢"
                elif signal.signal_type.value == "SELL":
                    self.stats["sell_signals"] += 1
                    icon = "🔴"
                else:
                    self.stats["hold_signals"] += 1
                    icon = "⚪"

                print(f"{icon} {strategy_name}: {signal.signal_type.value}")
                print(f"   Symbol: {signal.symbol}")
                print(f"   Price: ${signal.price:.2f}")
                print(f"   Quantity: {signal.quantity:.6f}")
                print(f"   Confidence: {signal.confidence:.2%}")

                if signal.metadata:
                    print(f"   Metadata: {signal.metadata}")

            except Exception as e:
                print(f"❌ Strategy {strategy_name} failed: {e}")
                self.stats["errors"] += 1

        print()

    def run_continuous_test(self):
        """Run continuous testing for specified duration."""
        print(f"🚀 Starting continuous dry run for {self.duration} seconds...\n")

        start_time = time.time()
        iteration = 0

        # Signal handler
        def signal_handler(signum, frame):
            print("\n⚠️  Interrupted by user")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)

        while self.running and (time.time() - start_time) < self.duration:
            iteration += 1
            elapsed = time.time() - start_time
            remaining = self.duration - elapsed

            print(f"📊 Iteration {iteration} - Elapsed: {elapsed:.0f}s - Remaining: {remaining:.0f}s")
            print("-" * 70)

            # Test strategy signals
            self.test_strategy_signals()

            # Progress update
            progress = (elapsed / self.duration) * 100
            print(f"Progress: {'█' * int(progress/5)}{' ' * (20-int(progress/5))} {progress:.1f}%\n")

            # Sleep between iterations
            if self.running and remaining > 30:
                print("💤 Sleeping for 30 seconds...\n")
                time.sleep(30)
            elif self.running:
                time.sleep(remaining)

        print("✅ Continuous test completed\n")

    def print_summary(self):
        """Print test summary."""
        print("=" * 70)
        print("📊 DRY RUN SUMMARY")
        print("=" * 70)
        print(f"Total signals generated: {self.stats['signals_generated']}")
        print(f"  🟢 Buy signals: {self.stats['buy_signals']}")
        print(f"  🔴 Sell signals: {self.stats['sell_signals']}")
        print(f"  ⚪ Hold signals: {self.stats['hold_signals']}")
        print(f"\nAPI calls made: {self.stats['api_calls']}")
        print(f"Errors encountered: {self.stats['errors']}")
        print("=" * 70)

        if self.stats["errors"] == 0:
            print("\n🎉 All tests passed successfully!")
            print("✅ Bot is ready for deployment")
        else:
            print(f"\n⚠️  {self.stats['errors']} errors occurred during testing")
            print("Please review the logs above")

        print("\nNext steps:")
        print("1. Review the signals generated above")
        print("2. Check if strategy behavior matches expectations")
        print("3. If satisfied, run: python -m src.main")
        print("4. Monitor closely for first 24-48 hours")
        print("=" * 70)

    def run(self):
        """Run full dry run test."""
        try:
            # Initial tests
            if not self.test_api_connectivity():
                print("❌ API connectivity test failed. Aborting.")
                return 1

            if not self.test_data_retrieval():
                print("⚠️  Data retrieval had issues but continuing...")

            # Run continuous test
            self.run_continuous_test()

            # Print summary
            self.print_summary()

            return 0 if self.stats["errors"] == 0 else 1

        except Exception as e:
            print(f"\n❌ Dry run failed with error: {e}")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Dry run testing for Binance trading bot")
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Test duration in seconds (default: 300 = 5 minutes)"
    )

    args = parser.parse_args()

    tester = DryRunTester(duration_seconds=args.duration)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
