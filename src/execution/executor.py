"""Order executor with rate limiting and retry logic."""

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from ..config import get_settings
from ..persistence import Database, OrderSide, OrderType, OrderStatus
from ..risk import RiskManager

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, max_requests: int = 10, time_window: int = 1):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]

        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.requests = []

        # Record this request
        self.requests.append(time.time())


class OrderExecutor:
    """Order executor with risk management and retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        risk_manager: Optional[RiskManager] = None,
        database: Optional[Database] = None
    ):
        """Initialize order executor.

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            risk_manager: Risk manager instance
            database: Database instance
        """
        settings = get_settings()
        self.api_key = api_key or settings.binance_api_key
        self.api_secret = api_secret or settings.binance_api_secret
        self.testnet = settings.binance_testnet

        # Initialize Binance client
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet
        )

        self.risk_manager = risk_manager or RiskManager()
        self.db = database or Database()

        # Rate limiter: 10 orders per second
        self.rate_limiter = RateLimiter(max_requests=10, time_window=1)

        logger.info(f"Order executor initialized (testnet={self.testnet})")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        strategy_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Tuple[bool, Optional[Dict], str]:
        """Place an order with risk checks.

        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            order_type: Order type (LIMIT/MARKET/etc)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            stop_price: Stop price (for stop orders)
            time_in_force: Time in force (GTC/IOC/FOK)
            strategy_name: Strategy name for tracking
            dry_run: If True, only simulate the order

        Returns:
            Tuple of (success, order_data, message)
        """
        # Risk check
        check_price = price or self._get_current_price(symbol)
        if check_price is None:
            return False, None, "Failed to get current price"

        approved, reason = self.risk_manager.check_order_approval(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=check_price
        )

        if not approved:
            logger.warning(f"Order rejected by risk manager: {reason}")
            return False, None, f"Risk check failed: {reason}"

        if dry_run:
            logger.info(f"DRY RUN: Would place order {symbol} {side} {quantity} @ {price}")
            return True, {"dry_run": True}, "Dry run successful"

        # Execute order
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed()

            # Place order on exchange
            order_result = self._execute_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=float(quantity),
                price=float(price) if price else None,
                stop_price=float(stop_price) if stop_price else None,
                time_in_force=time_in_force
            )

            # Save to database
            order_record = self._save_order(order_result, strategy_name)

            logger.info(
                f"Order placed successfully: {order_record.order_id} "
                f"({symbol} {side} {quantity} @ {price})"
            )

            return True, order_result, "Order placed successfully"

        except BinanceAPIException as e:
            error_msg = f"Binance API error: {e.message} (code: {e.code})"
            logger.error(error_msg)
            return False, None, error_msg

        except Exception as e:
            error_msg = f"Order execution failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(BinanceAPIException)
    )
    def _execute_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC"
    ) -> Dict:
        """Execute order on Binance (with retries).

        Args:
            symbol: Trading pair symbol
            side: Order side
            order_type: Order type
            quantity: Order quantity
            price: Order price
            stop_price: Stop price
            time_in_force: Time in force

        Returns:
            Order result from Binance
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "timeInForce": time_in_force
        }

        if price:
            params["price"] = price

        if stop_price:
            params["stopPrice"] = stop_price

        # Create order
        if order_type == "LIMIT":
            return self.client.create_order(**params)
        elif order_type == "MARKET":
            params.pop("timeInForce", None)  # Not needed for market orders
            params.pop("price", None)
            return self.client.create_order(**params)
        elif order_type in ["STOP_LOSS", "STOP_LOSS_LIMIT"]:
            return self.client.create_order(**params)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

    def cancel_order(self, symbol: str, order_id: str) -> Tuple[bool, str]:
        """Cancel an order.

        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel

        Returns:
            Tuple of (success, message)
        """
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed()

            # Cancel on exchange
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)

            # Update database
            self.db.update_order(order_id, {
                "status": OrderStatus.CANCELED,
                "updated_at": datetime.utcnow()
            })

            logger.info(f"Order cancelled: {order_id}")
            return True, "Order cancelled successfully"

        except BinanceAPIException as e:
            error_msg = f"Failed to cancel order: {e.message}"
            logger.error(error_msg)
            return False, error_msg

    def get_order_status(self, symbol: str, order_id: str) -> Optional[Dict]:
        """Get order status from exchange.

        Args:
            symbol: Trading pair symbol
            order_id: Order ID

        Returns:
            Order status or None
        """
        try:
            return self.client.get_order(symbol=symbol, orderId=order_id)
        except BinanceAPIException as e:
            logger.error(f"Failed to get order status: {e.message}")
            return None

    def sync_order_status(self, symbol: str, order_id: str):
        """Sync order status from exchange to database.

        Args:
            symbol: Trading pair symbol
            order_id: Order ID
        """
        try:
            order_status = self.get_order_status(symbol, order_id)
            if not order_status:
                return

            # Update database
            update_data = {
                "status": OrderStatus[order_status["status"]],
                "executed_qty": Decimal(str(order_status["executedQty"])),
                "cumulative_quote_qty": Decimal(str(order_status.get("cummulativeQuoteQty", 0))),
                "updated_at": datetime.utcnow()
            }

            self.db.update_order(order_id, update_data)

        except Exception as e:
            logger.error(f"Failed to sync order status: {e}")

    def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current market price for symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Current price or None
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return Decimal(str(ticker["price"]))
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    def _save_order(self, order_result: Dict, strategy_name: Optional[str] = None):
        """Save order to database.

        Args:
            order_result: Order result from Binance
            strategy_name: Strategy name

        Returns:
            Order database record
        """
        order_data = {
            "order_id": str(order_result["orderId"]),
            "client_order_id": order_result["clientOrderId"],
            "symbol": order_result["symbol"],
            "side": OrderSide[order_result["side"]],
            "order_type": OrderType[order_result["type"]],
            "status": OrderStatus[order_result["status"]],
            "price": Decimal(str(order_result.get("price", 0))) if order_result.get("price") else None,
            "quantity": Decimal(str(order_result["origQty"])),
            "executed_qty": Decimal(str(order_result.get("executedQty", 0))),
            "cumulative_quote_qty": Decimal(str(order_result.get("cummulativeQuoteQty", 0))),
            "time_in_force": order_result.get("timeInForce"),
            "transact_time": datetime.fromtimestamp(order_result["transactTime"] / 1000),
            "strategy_name": strategy_name
        }

        return self.db.create_order(order_data)

    def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all open orders for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Number of orders cancelled
        """
        try:
            open_orders = self.client.get_open_orders(symbol=symbol)
            cancelled_count = 0

            for order in open_orders:
                success, _ = self.cancel_order(symbol, str(order["orderId"]))
                if success:
                    cancelled_count += 1

            logger.info(f"Cancelled {cancelled_count} orders for {symbol}")
            return cancelled_count

        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return 0

    def sync_positions_from_exchange(self, trading_pairs: list) -> Dict[str, any]:
        """Sync positions from Binance exchange to local database.

        This is crucial for startup to ensure the bot is aware of existing positions
        that may have been opened manually or in a previous session.

        Args:
            trading_pairs: List of trading pairs to check (e.g., ['BTCUSDT', 'ETHUSDT'])

        Returns:
            Dictionary with sync results and statistics
        """
        logger.info("Syncing positions from Binance exchange...")

        sync_results = {
            'synced_count': 0,
            'created_count': 0,
            'updated_count': 0,
            'closed_count': 0,
            'discrepancies': [],
            'balances': {}
        }

        try:
            # Get account information from Binance
            account_info = self.client.get_account()

            # Extract balances
            balances = {
                balance['asset']: {
                    'free': Decimal(str(balance['free'])),
                    'locked': Decimal(str(balance['locked'])),
                    'total': Decimal(str(balance['free'])) + Decimal(str(balance['locked']))
                }
                for balance in account_info['balances']
                if Decimal(str(balance['free'])) > 0 or Decimal(str(balance['locked'])) > 0
            }

            sync_results['balances'] = balances

            # Check each trading pair
            for symbol in trading_pairs:
                # Extract base asset (e.g., 'BTC' from 'BTCUSDT')
                # Assumes quote currency is USDT, BTC, ETH, or BNB
                base_asset = None
                for quote in ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB']:
                    if symbol.endswith(quote):
                        base_asset = symbol[:-len(quote)]
                        quote_asset = quote
                        break

                if not base_asset:
                    logger.warning(f"Could not determine base asset for {symbol}")
                    continue

                # Get balance for this asset
                exchange_balance = balances.get(base_asset, {}).get('total', Decimal('0'))

                # Get current database position
                db_position = self.db.get_position(symbol)

                # Get current price for this symbol
                current_price = self._get_current_price(symbol)
                if not current_price:
                    logger.warning(f"Could not get current price for {symbol}, skipping sync")
                    continue

                # Sync logic
                if exchange_balance > Decimal('0.00000001'):  # Has balance on exchange
                    if db_position and db_position.is_open:
                        # Position exists in DB - check if quantities match
                        db_quantity = db_position.quantity or Decimal('0')

                        if abs(db_quantity - exchange_balance) > Decimal('0.00000001'):
                            # Discrepancy found
                            discrepancy = {
                                'symbol': symbol,
                                'db_quantity': float(db_quantity),
                                'exchange_quantity': float(exchange_balance),
                                'difference': float(exchange_balance - db_quantity)
                            }
                            sync_results['discrepancies'].append(discrepancy)

                            logger.warning(
                                f"Position mismatch for {symbol}: "
                                f"DB={db_quantity}, Exchange={exchange_balance}"
                            )

                            # Update database with exchange quantity
                            self.db.upsert_position(symbol, {
                                'quantity': exchange_balance,
                                'current_price': current_price,
                                'updated_at': datetime.utcnow()
                            })
                            sync_results['updated_count'] += 1
                        else:
                            # Quantities match, just update price
                            self.db.upsert_position(symbol, {
                                'current_price': current_price,
                                'updated_at': datetime.utcnow()
                            })

                    elif db_position and not db_position.is_open:
                        # Position exists but marked as closed - reopen it
                        logger.info(
                            f"Reopening closed position for {symbol} "
                            f"(found {exchange_balance} on exchange)"
                        )
                        self.db.upsert_position(symbol, {
                            'quantity': exchange_balance,
                            'current_price': current_price,
                            'is_open': True,
                            'updated_at': datetime.utcnow()
                        })
                        sync_results['updated_count'] += 1

                    else:
                        # No position in DB but has balance on exchange - create new position
                        logger.info(
                            f"Creating new position for {symbol} "
                            f"(found {exchange_balance} on exchange)"
                        )

                        # We don't know the exact entry price, so use current price as estimate
                        # This will affect PnL accuracy for pre-existing positions
                        position_data = {
                            'quantity': exchange_balance,
                            'entry_price': current_price,  # Estimated
                            'current_price': current_price,
                            'is_open': True,
                            'opened_at': datetime.utcnow(),
                            'notes': 'Position synced from exchange - entry price estimated'
                        }
                        self.db.upsert_position(symbol, position_data)
                        sync_results['created_count'] += 1

                        sync_results['discrepancies'].append({
                            'symbol': symbol,
                            'db_quantity': 0,
                            'exchange_quantity': float(exchange_balance),
                            'difference': float(exchange_balance),
                            'note': 'Position created from exchange balance'
                        })

                    sync_results['synced_count'] += 1

                else:
                    # No balance on exchange
                    if db_position and db_position.is_open:
                        # DB says open but exchange has no balance - close it
                        logger.warning(
                            f"Closing position for {symbol} "
                            f"(DB shows {db_position.quantity} but exchange has 0)"
                        )
                        self.db.upsert_position(symbol, {
                            'is_open': False,
                            'closed_at': datetime.utcnow(),
                            'current_price': current_price,
                            'notes': 'Closed during sync - no balance on exchange'
                        })
                        sync_results['closed_count'] += 1
                        sync_results['discrepancies'].append({
                            'symbol': symbol,
                            'db_quantity': float(db_position.quantity or 0),
                            'exchange_quantity': 0,
                            'difference': float(-(db_position.quantity or 0)),
                            'note': 'Position closed - no balance on exchange'
                        })

            # Log summary
            logger.info(
                f"Position sync complete: "
                f"synced={sync_results['synced_count']}, "
                f"created={sync_results['created_count']}, "
                f"updated={sync_results['updated_count']}, "
                f"closed={sync_results['closed_count']}, "
                f"discrepancies={len(sync_results['discrepancies'])}"
            )

            if sync_results['discrepancies']:
                logger.warning(f"Found {len(sync_results['discrepancies'])} discrepancies:")
                for disc in sync_results['discrepancies']:
                    logger.warning(f"  {disc}")

            return sync_results

        except BinanceAPIException as e:
            error_msg = f"Failed to sync positions from Binance: {e.message}"
            logger.error(error_msg)
            sync_results['error'] = error_msg
            return sync_results

        except Exception as e:
            error_msg = f"Failed to sync positions: {str(e)}"
            logger.error(error_msg)
            sync_results['error'] = error_msg
            return sync_results
