"""Test position synchronization from Binance exchange."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_position_sync():
    """Test syncing positions from Binance exchange to database."""
    from src.config import get_settings
    from src.execution import OrderExecutor
    from src.persistence import Database
    from src.risk import RiskManager
    from src.storage import RedisCache

    print("=" * 70)
    print("🔄 Testing Position Synchronization from Binance Exchange")
    print("=" * 70)
    print()

    settings = get_settings()

    print("📋 Configuration:")
    print(f"  Trading pairs: {', '.join(settings.trading_pairs_list)}")
    print(f"  Testnet: {settings.binance_testnet}")
    print()

    # Initialize components
    print("🔧 Initializing components...")
    db = Database()
    redis = RedisCache()
    risk_manager = RiskManager(redis_cache=redis, database=db)
    executor = OrderExecutor(risk_manager=risk_manager, database=db)
    print("  ✅ Components initialized")
    print()

    # Create tables if needed
    db.create_tables()

    # Show current database positions
    print("📊 Current Database Positions:")
    current_positions = db.get_all_positions(is_open=True)
    if current_positions:
        for pos in current_positions:
            print(f"  {pos.symbol}: {pos.quantity} @ ${pos.entry_price} (current: ${pos.current_price})")
    else:
        print("  No open positions in database")
    print()

    # Perform sync
    print("🔄 Syncing positions from Binance exchange...")
    print("-" * 70)
    sync_results = executor.sync_positions_from_exchange(
        trading_pairs=settings.trading_pairs_list
    )
    print()

    # Display results
    print("=" * 70)
    print("📈 Sync Results")
    print("=" * 70)
    print()

    if 'error' in sync_results:
        print(f"❌ Sync failed: {sync_results['error']}")
        return

    print(f"✅ Positions synced: {sync_results['synced_count']}")
    print(f"🆕 Positions created: {sync_results['created_count']}")
    print(f"📝 Positions updated: {sync_results['updated_count']}")
    print(f"🚫 Positions closed: {sync_results['closed_count']}")
    print()

    # Show balances found on exchange
    print("💰 Balances on Exchange:")
    if sync_results['balances']:
        for asset, balance in sync_results['balances'].items():
            if balance['total'] > 0:
                print(f"  {asset}: {balance['free']} free, {balance['locked']} locked (total: {balance['total']})")
    else:
        print("  No balances found")
    print()

    # Show discrepancies
    if sync_results['discrepancies']:
        print("⚠️  Discrepancies Found:")
        print("-" * 70)
        for disc in sync_results['discrepancies']:
            symbol = disc['symbol']
            db_qty = disc['db_quantity']
            exchange_qty = disc['exchange_quantity']
            diff = disc['difference']
            note = disc.get('note', '')

            print(f"  Symbol: {symbol}")
            print(f"    Database quantity: {db_qty}")
            print(f"    Exchange quantity: {exchange_qty}")
            print(f"    Difference: {diff}")
            if note:
                print(f"    Note: {note}")
            print()
    else:
        print("✅ No discrepancies found - database matches exchange!")
        print()

    # Show updated database positions
    print("📊 Updated Database Positions:")
    updated_positions = db.get_all_positions(is_open=True)
    if updated_positions:
        for pos in updated_positions:
            pnl = (pos.current_price - pos.entry_price) * pos.quantity if pos.current_price and pos.entry_price and pos.quantity else 0
            pnl_pct = ((pos.current_price - pos.entry_price) / pos.entry_price * 100) if pos.current_price and pos.entry_price else 0
            print(f"  {pos.symbol}:")
            print(f"    Quantity: {pos.quantity}")
            print(f"    Entry: ${pos.entry_price}")
            print(f"    Current: ${pos.current_price}")
            print(f"    PnL: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            if pos.notes:
                print(f"    Notes: {pos.notes}")
            print()
    else:
        print("  No open positions in database")
    print()

    print("=" * 70)
    print("🎉 Position synchronization test complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_position_sync()
