"""Quick health check script."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Quick health check."""
    print("🏥 Running health checks...\n")

    checks_passed = 0
    checks_failed = 0

    # Check 1: Redis
    print("1. Testing Redis connection...")
    try:
        from src.storage import RedisCache
        redis = RedisCache()
        if redis.health_check():
            print("   ✅ Redis is healthy\n")
            checks_passed += 1
        else:
            print("   ❌ Redis health check failed\n")
            checks_failed += 1
    except Exception as e:
        print(f"   ❌ Redis error: {e}\n")
        checks_failed += 1

    # Check 2: Database
    print("2. Testing database connection...")
    try:
        from src.persistence import Database
        db = Database()
        if db.health_check():
            print("   ✅ Database is healthy\n")
            checks_passed += 1
        else:
            print("   ❌ Database health check failed\n")
            checks_failed += 1
    except Exception as e:
        print(f"   ❌ Database error: {e}\n")
        checks_failed += 1

    # Check 3: Binance API
    print("3. Testing Binance API...")
    try:
        from src.data import BinanceDataClient
        client = BinanceDataClient()
        if client.ping():
            server_time = client.get_server_time()
            print(f"   ✅ Binance API is accessible (server time: {server_time})\n")
            checks_passed += 1
        else:
            print("   ❌ Binance API ping failed\n")
            checks_failed += 1
    except Exception as e:
        print(f"   ❌ Binance API error: {e}\n")
        checks_failed += 1

    # Summary
    print("=" * 50)
    print(f"Checks passed: {checks_passed}/3")
    print(f"Checks failed: {checks_failed}/3")
    print("=" * 50)

    if checks_failed == 0:
        print("\n🎉 All health checks passed!")
        return 0
    else:
        print(f"\n⚠️  {checks_failed} health check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
