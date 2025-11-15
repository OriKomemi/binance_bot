"""Test script for Ed25519 authentication."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_ed25519_auth():
    """Test Ed25519 authentication with Binance."""
    from src.data.binance_ed25519_client import BinanceEd25519Client
    from src.config import get_settings

    print("🔐 Testing Ed25519 Authentication\n")

    settings = get_settings()

    if not settings.use_ed25519:
        print("❌ Ed25519 is not enabled in .env")
        print("\nTo enable Ed25519:")
        print("1. Set USE_ED25519=true in .env")
        print("2. Set ED25519_PRIVATE_KEY_PATH=path/to/your/key.pem")
        print("3. Optionally set ED25519_KEY_PASSWORD if key is encrypted")
        return False

    if not settings.ed25519_private_key_path:
        print("❌ ED25519_PRIVATE_KEY_PATH not set in .env")
        return False

    try:
        # Initialize client
        print("Initializing Ed25519 client...")
        client = BinanceEd25519Client(
            api_key=settings.binance_api_key,
            private_key_path=settings.ed25519_private_key_path,
            testnet=settings.binance_testnet,
            password=settings.ed25519_key_password or None
        )
        print("✅ Client initialized\n")

        # Test 1: Ping
        print("1. Testing ping...")
        if client.ping():
            print("   ✅ Ping successful\n")
        else:
            print("   ❌ Ping failed\n")
            return False

        # Test 2: Server time
        print("2. Getting server time...")
        server_time = client.get_server_time()
        from datetime import datetime
        dt = datetime.fromtimestamp(server_time / 1000)
        print(f"   ✅ Server time: {dt}\n")

        # Test 3: Ticker price
        print("3. Getting BTC price...")
        ticker = client.get_ticker_price("BTCUSDT")
        print(f"   ✅ BTC Price: ${ticker['price']}\n")

        # Test 4: Account info (signed request)
        print("4. Getting account info (signed request)...")
        account = client.get_account()
        print(f"   ✅ Account retrieved")
        print(f"   Balances: {len(account.get('balances', []))}")

        # Show USDT balance if available
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                print(f"   USDT Balance: {balance['free']}")
                break
        print()

        # Test 5: Get open orders
        print("5. Getting open orders...")
        open_orders = client.get_open_orders()
        print(f"   ✅ Open orders: {len(open_orders)}\n")

        print("=" * 50)
        print("🎉 All Ed25519 authentication tests passed!")
        print("=" * 50)
        print("\nYour Ed25519 authentication is working correctly.")
        print("The bot can now use secure Ed25519 signing for all API requests.")

        return True

    except FileNotFoundError as e:
        print(f"❌ Private key file not found: {e}")
        print("\nMake sure:")
        print("1. The key file exists at the specified path")
        print("2. The path in .env is correct")
        return False

    except ValueError as e:
        print(f"❌ Invalid key file: {e}")
        print("\nMake sure:")
        print("1. The file contains a valid Ed25519 private key")
        print("2. The key is in PEM format")
        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    result = test_ed25519_auth()
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
