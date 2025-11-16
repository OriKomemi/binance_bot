"""Diagnostic script to test Binance API connection."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_binance_connection():
    """Test Binance API connection and authentication."""
    print("=" * 70)
    print("🔧 Binance API Connection Diagnostic")
    print("=" * 70)
    print()

    from src.config import get_settings
    from src.execution import OrderExecutor
    from src.persistence import Database
    from src.risk import RiskManager
    from src.storage import RedisCache

    settings = get_settings()

    print("📋 Configuration:")
    print(f"  Testnet: {settings.binance_testnet}")
    print(f"  Use Ed25519: {settings.use_ed25519}")
    print(f"  API Key: {settings.binance_api_key[:10]}..." if settings.binance_api_key else "  API Key: NOT SET")
    if settings.use_ed25519:
        print(f"  Ed25519 Key Path: {settings.ed25519_private_key_path}")
    else:
        print(f"  API Secret: {'SET' if settings.binance_api_secret else 'NOT SET'}")
    print()

    # Initialize components
    print("🔧 Initializing components...")
    try:
        db = Database()
        redis = RedisCache()
        risk_manager = RiskManager(redis_cache=redis, database=db)
        executor = OrderExecutor(risk_manager=risk_manager, database=db)
        print("  ✅ Components initialized successfully")
        print()
    except Exception as e:
        print(f"  ❌ Failed to initialize components: {e}")
        print()
        return

    # Test 1: Ping
    print("📡 Test 1: Testing API connectivity (ping)...")
    try:
        if hasattr(executor.client, 'ping'):
            result = executor.client.ping()
            print(f"  ✅ Ping successful: {result}")
        else:
            print("  ⚠️  Client doesn't have ping method, skipping")
    except Exception as e:
        print(f"  ❌ Ping failed: {e}")
        print("  💡 Check your internet connection and Binance API endpoint")
    print()

    # Test 2: Server Time
    print("🕐 Test 2: Getting server time...")
    try:
        if hasattr(executor.client, 'get_server_time'):
            server_time = executor.client.get_server_time()
            print(f"  ✅ Server time: {server_time}")
        else:
            print("  ⚠️  Client doesn't have get_server_time method")
    except Exception as e:
        print(f"  ❌ Failed to get server time: {e}")
    print()

    # Test 3: Account Information (requires authentication)
    print("🔐 Test 3: Getting account information (requires authentication)...")
    try:
        account_info = executor.client.get_account()

        # Count balances
        if 'balances' in account_info:
            non_zero_balances = [
                b for b in account_info['balances']
                if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0
            ]
            print(f"  ✅ Account info retrieved successfully")
            print(f"  📊 Account has {len(non_zero_balances)} assets with non-zero balance")

            if non_zero_balances:
                print(f"  💰 Assets found:")
                for balance in non_zero_balances[:5]:  # Show first 5
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    print(f"     {asset}: {total:.8f} (free: {free:.8f}, locked: {locked:.8f})")

                if len(non_zero_balances) > 5:
                    print(f"     ... and {len(non_zero_balances) - 5} more")
        else:
            print(f"  ✅ Account info retrieved (no balance data)")

    except Exception as e:
        print(f"  ❌ Failed to get account info: {e}")
        print()
        print("  💡 Troubleshooting:")
        if settings.use_ed25519:
            print("     - Check that ED25519_PRIVATE_KEY_PATH is correct")
            print("     - Verify the private key file exists and is readable")
            print("     - Make sure the API key matches the Ed25519 key")
            print("     - Check if ED25519_KEY_PASSWORD is needed")
        else:
            print("     - Verify BINANCE_API_KEY is correct")
            print("     - Verify BINANCE_API_SECRET is correct")
            print("     - Make sure API key has the required permissions")
            print("     - For testnet, ensure you're using testnet credentials")
        return
    print()

    # Test 4: Get ticker price (public endpoint)
    print("📈 Test 4: Getting ticker price for BTCUSDT...")
    try:
        if hasattr(executor.client, 'get_symbol_ticker'):
            ticker = executor.client.get_symbol_ticker(symbol='BTCUSDT')
            price = float(ticker.get('price', 0))
            print(f"  ✅ BTCUSDT price: ${price:,.2f}")
        elif hasattr(executor.client, 'get_ticker_price'):
            ticker = executor.client.get_ticker_price(symbol='BTCUSDT')
            price = float(ticker.get('price', 0))
            print(f"  ✅ BTCUSDT price: ${price:,.2f}")
        else:
            print("  ⚠️  Client doesn't have ticker methods")
    except Exception as e:
        print(f"  ❌ Failed to get ticker: {e}")
    print()

    # Test 5: Get 24hr stats
    print("📊 Test 5: Getting 24hr ticker stats for BTCUSDT...")
    try:
        if hasattr(executor.client, 'get_ticker'):
            ticker_24h = executor.client.get_ticker(symbol='BTCUSDT')
            price_change = float(ticker_24h.get('priceChangePercent', 0))
            volume = float(ticker_24h.get('volume', 0))
            print(f"  ✅ 24h change: {price_change:+.2f}%")
            print(f"  ✅ 24h volume: {volume:,.2f} BTC")
        else:
            print("  ⚠️  Client doesn't have get_ticker method")
    except Exception as e:
        print(f"  ❌ Failed to get 24hr stats: {e}")
    print()

    # Test 6: Position sync
    print("🔄 Test 6: Testing position sync functionality...")
    try:
        sync_results = executor.sync_positions_from_exchange(
            trading_pairs=settings.trading_pairs_list
        )

        if 'error' in sync_results:
            print(f"  ❌ Sync failed: {sync_results['error']}")
        else:
            print(f"  ✅ Position sync successful")
            print(f"     Synced: {sync_results['synced_count']}")
            print(f"     Created: {sync_results['created_count']}")
            print(f"     Updated: {sync_results['updated_count']}")
            print(f"     Closed: {sync_results['closed_count']}")
            print(f"     Discrepancies: {len(sync_results.get('discrepancies', []))}")

            if sync_results.get('discrepancies'):
                print(f"  ⚠️  Found discrepancies:")
                for disc in sync_results['discrepancies'][:3]:  # Show first 3
                    print(f"     {disc}")
    except Exception as e:
        print(f"  ❌ Position sync failed: {e}")
    print()

    # Summary
    print("=" * 70)
    print("✅ Diagnostic Complete!")
    print("=" * 70)
    print()
    print("📝 Summary:")
    print("  If all tests passed, your Binance API connection is working correctly.")
    print("  The Telegram bot should now be able to:")
    print("    - Get account balances (/balance)")
    print("    - Sync positions (/sync)")
    print("    - Get prices (/price)")
    print("    - Show market data (/market)")
    print()
    print("  Start your bot with: python -m src.main")
    print("  Then test Telegram commands: /status, /balance, /positions")
    print()


if __name__ == "__main__":
    test_binance_connection()
