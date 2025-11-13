"""Dollar Cost Averaging (DCA) strategy - buy at regular intervals."""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal, SignalType

logger = logging.getLogger(__name__)


class DCAStrategy(BaseStrategy):
    """Dollar Cost Averaging strategy for gradual position building."""

    def __init__(
        self,
        symbol: str,
        purchase_amount_usd: float = 100.0,
        interval_hours: int = 24,
        price_drop_threshold_percent: float = 2.0,
        **kwargs
    ):
        """Initialize DCA strategy.

        Args:
            symbol: Trading pair symbol
            purchase_amount_usd: Amount to purchase each interval
            interval_hours: Hours between purchases
            price_drop_threshold_percent: Extra buy if price drops by this percent
        """
        parameters = {
            "purchase_amount_usd": purchase_amount_usd,
            "interval_hours": interval_hours,
            "price_drop_threshold_percent": price_drop_threshold_percent,
            **kwargs
        }

        super().__init__(name="DCAStrategy", symbol=symbol, parameters=parameters)

        self.last_purchase_time: Optional[datetime] = None
        self.last_purchase_price: Optional[Decimal] = None
        self.average_cost: Optional[Decimal] = None
        self.total_invested: Decimal = Decimal("0")
        self.total_quantity: Decimal = Decimal("0")

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators (simple moving average for context).

        Args:
            df: OHLCV DataFrame

        Returns:
            DataFrame with indicators
        """
        # Calculate simple moving average for reference
        df["sma_7"] = df["close"].rolling(window=7).mean()
        df["sma_25"] = df["close"].rolling(window=25).mean()

        return df

    def generate_signal(self, market_data: pd.DataFrame) -> Signal:
        """Generate DCA signal.

        Args:
            market_data: DataFrame with OHLCV data

        Returns:
            Trading signal
        """
        if not self.validate_data(market_data):
            return self._hold_signal(market_data)

        current_price = Decimal(str(market_data.iloc[-1]["close"]))
        timestamp = market_data.iloc[-1]["timestamp"]

        # Check if it's time for regular DCA purchase
        if self._should_make_regular_purchase(timestamp):
            quantity = self._calculate_purchase_quantity(current_price)
            signal = Signal(
                signal_type=SignalType.BUY,
                symbol=self.symbol,
                price=current_price,
                quantity=quantity,
                timestamp=timestamp,
                metadata={
                    "strategy": "dca",
                    "reason": "regular_interval",
                    "average_cost": float(self.average_cost) if self.average_cost else None
                }
            )
            self.record_signal(signal)
            return signal

        # Check for opportunistic purchase on price drop
        if self._should_buy_on_dip(current_price):
            # Buy extra on significant dip
            quantity = self._calculate_purchase_quantity(current_price) * Decimal("1.5")
            signal = Signal(
                signal_type=SignalType.BUY,
                symbol=self.symbol,
                price=current_price,
                quantity=quantity,
                timestamp=timestamp,
                metadata={
                    "strategy": "dca",
                    "reason": "price_dip",
                    "drop_percent": float(self._calculate_price_drop_percent(current_price))
                }
            )
            self.record_signal(signal)
            return signal

        # Otherwise hold
        signal = self._hold_signal(market_data)
        self.record_signal(signal)
        return signal

    def _should_make_regular_purchase(self, current_time: datetime) -> bool:
        """Check if it's time for regular DCA purchase.

        Args:
            current_time: Current timestamp

        Returns:
            True if should make purchase
        """
        if self.last_purchase_time is None:
            return True

        interval_hours = self.get_parameter("interval_hours")
        time_since_last = current_time - self.last_purchase_time
        required_interval = timedelta(hours=interval_hours)

        return time_since_last >= required_interval

    def _should_buy_on_dip(self, current_price: Decimal) -> bool:
        """Check if should buy on price dip.

        Args:
            current_price: Current price

        Returns:
            True if should buy
        """
        if self.last_purchase_price is None:
            return False

        drop_threshold = Decimal(str(self.get_parameter("price_drop_threshold_percent")))
        price_drop_percent = self._calculate_price_drop_percent(current_price)

        return price_drop_percent >= drop_threshold

    def _calculate_price_drop_percent(self, current_price: Decimal) -> Decimal:
        """Calculate price drop percentage from last purchase.

        Args:
            current_price: Current price

        Returns:
            Drop percentage (positive number)
        """
        if self.last_purchase_price is None or self.last_purchase_price == 0:
            return Decimal("0")

        drop = ((self.last_purchase_price - current_price) / self.last_purchase_price) * 100
        return max(drop, Decimal("0"))  # Only positive drops

    def _calculate_purchase_quantity(self, price: Decimal) -> Decimal:
        """Calculate purchase quantity.

        Args:
            price: Purchase price

        Returns:
            Quantity to purchase
        """
        purchase_amount = Decimal(str(self.get_parameter("purchase_amount_usd")))
        quantity = purchase_amount / price
        return quantity

    def record_purchase(
        self,
        price: Decimal,
        quantity: Decimal,
        timestamp: datetime
    ):
        """Record a purchase for DCA tracking.

        Args:
            price: Purchase price
            quantity: Quantity purchased
            timestamp: Purchase time
        """
        # Update totals
        cost = price * quantity
        self.total_invested += cost
        self.total_quantity += quantity

        # Calculate new average cost
        if self.total_quantity > 0:
            self.average_cost = self.total_invested / self.total_quantity

        # Update last purchase
        self.last_purchase_time = timestamp
        self.last_purchase_price = price

        logger.info(
            f"DCA purchase recorded: {quantity} @ {price} "
            f"(avg cost: {self.average_cost:.2f}, total: {self.total_quantity})"
        )

    def _hold_signal(self, market_data: pd.DataFrame) -> Signal:
        """Generate HOLD signal.

        Args:
            market_data: Market data

        Returns:
            HOLD signal
        """
        current_price = Decimal(str(market_data.iloc[-1]["close"]))
        timestamp = market_data.iloc[-1]["timestamp"]

        return Signal(
            signal_type=SignalType.HOLD,
            symbol=self.symbol,
            price=current_price,
            quantity=Decimal("0"),
            timestamp=timestamp,
            metadata={
                "strategy": "dca",
                "average_cost": float(self.average_cost) if self.average_cost else None,
                "total_quantity": float(self.total_quantity)
            }
        )

    def get_performance(self, current_price: Decimal) -> Dict:
        """Get DCA performance metrics.

        Args:
            current_price: Current market price

        Returns:
            Performance metrics
        """
        if self.total_quantity == 0:
            return {"status": "no_positions"}

        current_value = self.total_quantity * current_price
        profit_loss = current_value - self.total_invested
        profit_loss_percent = (profit_loss / self.total_invested) * 100 if self.total_invested > 0 else Decimal("0")

        return {
            "total_invested": float(self.total_invested),
            "total_quantity": float(self.total_quantity),
            "average_cost": float(self.average_cost),
            "current_price": float(current_price),
            "current_value": float(current_value),
            "profit_loss": float(profit_loss),
            "profit_loss_percent": float(profit_loss_percent)
        }
