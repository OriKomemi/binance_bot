"""Test enhanced Telegram visualizations."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_portfolio_status():
    """Test portfolio status visualization."""
    from src.monitoring import TelegramNotifier

    print("📊 Testing Portfolio Status Visualization...\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram not enabled. Set credentials in .env to test.")
        return

    # Sample portfolio data
    portfolio_data = {
        'total_value': 10500.00,
        'total_pnl': 500.00,
        'pnl_percent': 5.00,
        'daily_pnl': 125.50,
        'daily_trades': 8,
        'win_rate': 62.5,
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'quantity': 0.05,
                'entry_price': 42000.00,
                'current_price': 43500.00,
                'pnl': 75.00,
                'pnl_percent': 3.57
            },
            {
                'symbol': 'ETHUSDT',
                'quantity': 1.5,
                'entry_price': 2200.00,
                'current_price': 2350.00,
                'pnl': 225.00,
                'pnl_percent': 6.82
            },
            {
                'symbol': 'BNBUSDT',
                'quantity': 10.0,
                'entry_price': 310.00,
                'current_price': 305.00,
                'pnl': -50.00,
                'pnl_percent': -1.61
            }
        ]
    }

    notifier.send_portfolio_status(portfolio_data)
    print("✅ Portfolio status sent!\n")


def test_trade_summary():
    """Test trade summary visualization."""
    from src.monitoring import TelegramNotifier

    print("💹 Testing Trade Summary Visualization...\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram not enabled. Set credentials in .env to test.")
        return

    # Sample winning trade
    trade_data = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 42000.00,
        'exit_price': 43500.00,
        'quantity': 0.05,
        'pnl': 75.00,
        'pnl_percent': 3.57,
        'duration': '4h 23m',
        'strategy': 'Grid Trading'
    }

    notifier.send_trade_summary(trade_data)
    print("✅ Trade summary sent!\n")


def test_performance_chart():
    """Test performance chart visualization."""
    from src.monitoring import TelegramNotifier

    print("📈 Testing Performance Chart...\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram not enabled. Set credentials in .env to test.")
        return

    # Sample performance data
    performance_data = {
        'pnl_history': [50, 75, -20, 120, 80, 150, 200],  # Last 7 days
        'win_streak': 3,
        'loss_streak': 1,
        'best_trade': 250.00,
        'worst_trade': -45.00,
        'avg_win': 95.50,
        'avg_loss': 32.00,
        'total_trades': 25,
        'winning_trades': 16,
        'losing_trades': 9
    }

    notifier.send_performance_chart(performance_data)
    print("✅ Performance chart sent!\n")


def test_market_overview():
    """Test market overview visualization."""
    from src.monitoring import TelegramNotifier

    print("🌐 Testing Market Overview...\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram not enabled. Set credentials in .env to test.")
        return

    # Sample market data
    market_data = {
        'symbols': [
            {
                'symbol': 'BTCUSDT',
                'price': 43500.00,
                'change_24h': 3.5,
                'volume_24h': 25600000000
            },
            {
                'symbol': 'ETHUSDT',
                'price': 2350.00,
                'change_24h': -1.2,
                'volume_24h': 12400000000
            },
            {
                'symbol': 'BNBUSDT',
                'price': 305.00,
                'change_24h': 0.8,
                'volume_24h': 850000000
            }
        ]
    }

    notifier.send_market_overview(market_data)
    print("✅ Market overview sent!\n")


def test_risk_dashboard():
    """Test risk dashboard visualization."""
    from src.monitoring import TelegramNotifier

    print("🛡️  Testing Risk Dashboard...\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram not enabled. Set credentials in .env to test.")
        return

    # Sample risk data
    risk_data = {
        'total_exposure': 3500.00,
        'max_exposure': 5000.00,
        'daily_loss': 75.00,
        'max_daily_loss': 200.00,
        'positions_count': 3,
        'circuit_breaker_active': False
    }

    notifier.send_risk_dashboard(risk_data)
    print("✅ Risk dashboard sent!\n")


def main():
    """Run all visualization tests."""
    print("=" * 60)
    print("🎨 Testing Enhanced Telegram Visualizations")
    print("=" * 60)
    print()

    tests = [
        ("Portfolio Status", test_portfolio_status),
        ("Trade Summary", test_trade_summary),
        ("Performance Chart", test_performance_chart),
        ("Market Overview", test_market_overview),
        ("Risk Dashboard", test_risk_dashboard),
    ]

    print("This will send 5 different visualization messages to your Telegram.")
    print("Make sure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env")
    print()

    import time

    for name, test_func in tests:
        print(f"🎯 {name}")
        print("-" * 60)
        test_func()
        time.sleep(2)  # Pause between messages

    print("=" * 60)
    print("🎉 All visualization tests complete!")
    print("Check your Telegram for 5 beautifully formatted messages:")
    print("  1. Portfolio Status with positions and PnL")
    print("  2. Trade Summary with price action")
    print("  3. Performance Chart with sparklines")
    print("  4. Market Overview with trends")
    print("  5. Risk Dashboard with gauges")
    print("=" * 60)


if __name__ == "__main__":
    main()
