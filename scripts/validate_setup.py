"""Setup validation script - Check all prerequisites."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_env_file():
    """Check if .env file exists."""
    print("🔍 Checking environment file...")
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Create one using: cp .env.example .env")
        return False

    print("✅ .env file found")
    return True


def check_environment_variables():
    """Check required environment variables."""
    print("\n🔍 Checking environment variables...")

    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "POSTGRES_HOST",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "REDIS_HOST"
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"❌ Missing: {var}")
        else:
            # Mask sensitive values
            if "SECRET" in var or "PASSWORD" in var:
                display_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var} = {display_value}")

    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        return False

    print("✅ All required environment variables set")
    return True


def check_redis_connection():
    """Check Redis connectivity."""
    print("\n🔍 Checking Redis connection...")

    try:
        from src.storage import RedisCache
        redis_cache = RedisCache()

        if redis_cache.health_check():
            print("✅ Redis connection successful")
            return True
        else:
            print("❌ Redis health check failed")
            return False

    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Make sure Redis is running:")
        print("   - Docker: docker-compose up -d redis")
        print("   - Local: sudo service redis-server start")
        return False


def check_database_connection():
    """Check PostgreSQL connectivity."""
    print("\n🔍 Checking database connection...")

    try:
        from src.persistence import Database
        db = Database()

        if db.health_check():
            print("✅ Database connection successful")

            # Try to create tables
            print("   Creating database tables...")
            db.create_tables()
            print("✅ Database tables created")
            return True
        else:
            print("❌ Database health check failed")
            return False

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Make sure PostgreSQL is running:")
        print("   - Docker: docker-compose up -d postgres")
        print("   - Local: sudo service postgresql start")
        return False


def check_binance_api():
    """Check Binance API connectivity."""
    print("\n🔍 Checking Binance API connection...")

    try:
        from src.data import BinanceDataClient
        client = BinanceDataClient()

        # Test ping
        if client.ping():
            print("✅ Binance API ping successful")

            # Get server time
            server_time = client.get_server_time()
            print(f"✅ Server time: {server_time}")

            # Test getting ticker
            try:
                ticker = client.get_ticker_price("BTCUSDT")
                print(f"✅ Got BTC price: ${ticker['price']}")
                return True
            except Exception as e:
                print(f"⚠️  Could not get ticker (might be testnet limitation): {e}")
                return True  # Still consider it a success if ping worked

        else:
            print("❌ Binance API ping failed")
            return False

    except Exception as e:
        print(f"❌ Binance API connection failed: {e}")
        print("   Check your API credentials in .env")
        return False


def check_dependencies():
    """Check if all required packages are installed."""
    print("\n🔍 Checking Python dependencies...")

    required_packages = [
        "binance",
        "websockets",
        "pandas",
        "redis",
        "sqlalchemy",
        "psycopg2",
        "pyyaml",
        "pydantic",
        "prometheus_client",
        "telegram",
        "pyarrow"
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package}")

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install -r requirements.txt")
        return False

    print("✅ All dependencies installed")
    return True


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("🚀 Binance Trading Bot - Setup Validation")
    print("=" * 60)

    checks = [
        ("Environment File", check_env_file),
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_dependencies),
        ("Redis Connection", check_redis_connection),
        ("Database Connection", check_database_connection),
        ("Binance API", check_binance_api),
    ]

    results = {}

    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 Validation Summary")
    print("=" * 60)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All checks passed! You're ready to run the bot.")
        print("\nNext steps:")
        print("1. Run dry-run test: python scripts/dry_run.py")
        print("2. Start the bot: python -m src.main")
        print("=" * 60)
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
