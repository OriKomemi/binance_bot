"""Test Binance API connectivity."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BinanceDataClient
from datetime import datetime, timedelta


def main():
    """Test Binance API."""
    print("🔗 Testing Binance API Connection\n")

    try:
        client = BinanceDataClient()

        # Test 1: Ping
        print("1. Testing ping...")
        if client.ping():
            print("   ✅ Ping successful\n")
        else:
            print("   ❌ Ping failed\n")
            return 1

        # Test 2: Server time
        print("2. Getting server time...")
        server_time = client.get_server_time()
        server_dt = datetime.fromtimestamp(server_time / 1000)
        print(f"   ✅ Server time: {server_dt}\n")

        # Test 3: Exchange info
        print("3. Getting exchange info...")
        info = client.get_exchange_info(symbol="BTCUSDT")
        print(f"   ✅ Exchange info retrieved")
        print(f"   Symbol: {info['symbol']}")
        print(f"   Status: {info['status']}\n")

        # Test 4: Get ticker price
        print("4. Getting current BTC price...")
        ticker = client.get_ticker_price("BTCUSDT")
        print(f"   ✅ BTC Price: ${ticker['price']}\n")

        # Test 5: Get 24h ticker
        print("5. Getting 24h ticker stats...")
        ticker_24h = client.get_24h_ticker("BTCUSDT")
        print(f"   ✅ 24h Stats:")
        print(f"   High: ${float(ticker_24h['highPrice']):.2f}")
        print(f"   Low: ${float(ticker_24h['lowPrice']):.2f}")
        print(f"   Volume: {float(ticker_24h['volume']):.2f} BTC\n")

        # Test 6: Get recent klines
        print("6. Getting recent klines...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        df = client.get_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_time=start_time,
            end_time=end_time,
            limit=60
        )
        print(f"   ✅ Retrieved {len(df)} klines")
        print(f"   Latest close: ${df.iloc[-1]['close']:.2f}\n")

        # Test 7: Get orderbook
        print("7. Getting orderbook...")
        orderbook = client.get_orderbook("BTCUSDT", limit=5)
        print(f"   ✅ Orderbook retrieved")
        print(f"   Top bid: ${float(orderbook['bids'][0][0]):.2f}")
        print(f"   Top ask: ${float(orderbook['asks'][0][0]):.2f}\n")

        print("=" * 50)
        print("🎉 All Binance API tests passed!")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"\n❌ Binance API test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API credentials in .env")
        print("2. Verify BINANCE_TESTNET setting")
        print("3. Check internet connectivity")
        print("4. Verify API key has correct permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
