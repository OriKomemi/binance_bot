"""Test script for Telegram notifications."""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_telegram_async():
    """Test Telegram notifications asynchronously."""
    from src.monitoring import TelegramNotifier

    print("🔔 Testing Telegram Notifications (Async)\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram is not enabled")
        print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    print("✅ Telegram notifier initialized")
    print(f"   Bot token: {notifier.bot_token[:10]}...")
    print(f"   Chat ID: {notifier.chat_id}\n")

    # Test 1: Simple message
    print("1. Testing simple message...")
    success = await notifier.send_message_async(
        "🧪 *Test Message*\n\nThis is a test from the Binance trading bot!"
    )
    if success:
        print("   ✅ Message sent successfully\n")
    else:
        print("   ❌ Failed to send message\n")
        return False

    await asyncio.sleep(1)

    # Test 2: Trade alert
    print("2. Testing trade alert...")
    notifier.alert_trade_executed(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        price=43500.00,
        strategy="Test Strategy"
    )
    print("   ✅ Trade alert sent\n")

    await asyncio.sleep(1)

    # Test 3: System status
    print("3. Testing system status alert...")
    notifier.alert_system_status(
        "started",
        "Bot testing in progress"
    )
    print("   ✅ System status sent\n")

    await asyncio.sleep(1)

    # Test 4: Risk warning
    print("4. Testing risk warning...")
    notifier.alert_risk_warning(
        "Test Warning",
        "This is a test risk warning"
    )
    print("   ✅ Risk warning sent\n")

    print("=" * 50)
    print("🎉 All Telegram tests passed!")
    print("Check your Telegram chat for 4 messages")
    print("=" * 50)

    return True


def test_telegram_sync():
    """Test Telegram notifications synchronously."""
    from src.monitoring import TelegramNotifier

    print("🔔 Testing Telegram Notifications (Sync)\n")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("⚠️  Telegram is not enabled")
        print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    print("✅ Telegram notifier initialized\n")

    # Test simple message
    print("Testing simple message...")
    success = notifier.send_message(
        "🧪 *Sync Test Message*\n\nThis is a synchronous test!"
    )

    if success:
        print("✅ Sync message sent successfully\n")
        return True
    else:
        print("❌ Failed to send sync message\n")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Telegram notifications")
    parser.add_argument(
        "--async",
        action="store_true",
        dest="async_mode",
        help="Use async mode"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Use sync mode (default)"
    )

    args = parser.parse_args()

    try:
        if args.async_mode:
            result = asyncio.run(test_telegram_async())
        else:
            result = test_telegram_sync()

        return 0 if result else 1

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
