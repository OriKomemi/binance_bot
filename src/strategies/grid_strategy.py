"""Grid trading strategy - places buy/sell orders at predetermined price levels."""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal, SignalType

logger = logging.getLogger(__name__)


class GridStrategy(BaseStrategy):
    """Grid trading strategy for ranging markets."""

    def __init__(
        self,
        symbol: str,
        grid_levels: int = 10,
        price_range_percent: float = 5.0,
        position_size_usd: float = 100.0,
        **kwargs
    ):
        """Initialize grid strategy.

        Args:
            symbol: Trading pair symbol
            grid_levels: Number of grid levels
            price_range_percent: Price range as percentage (e.g., 5 for ±5%)
            position_size_usd: Position size per grid level in USD
        """
        parameters = {
            "grid_levels": grid_levels,
            "price_range_percent": price_range_percent,
            "position_size_usd": position_size_usd,
            **kwargs
        }

        super().__init__(name="GridStrategy", symbol=symbol, parameters=parameters)

        self.grid_prices: List[Decimal] = []
        self.active_orders: Dict[Decimal, str] = {}  # price -> order_id
        self.center_price: Optional[Decimal] = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators (not needed for basic grid).

        Args:
            df: OHLCV DataFrame

        Returns:
            DataFrame with indicators
        """
        # Grid strategy doesn't need technical indicators
        # Just use price data
        return df

    def generate_signal(self, market_data: pd.DataFrame) -> Signal:
        """Generate grid trading signal.

        Args:
            market_data: DataFrame with OHLCV data

        Returns:
            Trading signal
        """
        if not self.validate_data(market_data):
            return self._hold_signal(market_data)

        current_price = Decimal(str(market_data.iloc[-1]["close"]))
        timestamp = market_data.iloc[-1]["timestamp"]

        # Initialize grid if not set
        if not self.grid_prices:
            self._initialize_grid(current_price)

        # Find nearest grid levels
        lower_grid = self._find_lower_grid(current_price)
        upper_grid = self._find_upper_grid(current_price)

        # Determine signal based on price position
        if lower_grid and self._should_buy_at_level(current_price, lower_grid):
            quantity = self._calculate_grid_quantity(current_price)
            signal = Signal(
                signal_type=SignalType.BUY,
                symbol=self.symbol,
                price=current_price,
                quantity=quantity,
                timestamp=timestamp,
                metadata={"grid_level": float(lower_grid), "strategy": "grid"}
            )
        elif upper_grid and self._should_sell_at_level(current_price, upper_grid):
            quantity = self._calculate_grid_quantity(current_price)
            signal = Signal(
                signal_type=SignalType.SELL,
                symbol=self.symbol,
                price=current_price,
                quantity=quantity,
                timestamp=timestamp,
                metadata={"grid_level": float(upper_grid), "strategy": "grid"}
            )
        else:
            signal = self._hold_signal(market_data)

        self.record_signal(signal)
        return signal

    def _initialize_grid(self, center_price: Decimal):
        """Initialize grid levels around center price.

        Args:
            center_price: Center price for grid
        """
        self.center_price = center_price
        grid_levels = self.get_parameter("grid_levels")
        price_range_percent = Decimal(str(self.get_parameter("price_range_percent")))

        # Calculate price range
        price_range = center_price * (price_range_percent / Decimal("100"))

        # Calculate grid spacing
        grid_spacing = (price_range * 2) / Decimal(str(grid_levels - 1))

        # Create grid levels
        self.grid_prices = []
        for i in range(grid_levels):
            level_price = (center_price - price_range) + (grid_spacing * Decimal(str(i)))
            self.grid_prices.append(level_price)

        logger.info(
            f"Initialized grid: {grid_levels} levels from "
            f"{self.grid_prices[0]:.2f} to {self.grid_prices[-1]:.2f} "
            f"(center: {center_price:.2f})"
        )

    def _find_lower_grid(self, current_price: Decimal) -> Optional[Decimal]:
        """Find nearest lower grid level.

        Args:
            current_price: Current market price

        Returns:
            Lower grid level or None
        """
        lower_levels = [price for price in self.grid_prices if price < current_price]
        return max(lower_levels) if lower_levels else None

    def _find_upper_grid(self, current_price: Decimal) -> Optional[Decimal]:
        """Find nearest upper grid level.

        Args:
            current_price: Current market price

        Returns:
            Upper grid level or None
        """
        upper_levels = [price for price in self.grid_prices if price > current_price]
        return min(upper_levels) if upper_levels else None

    def _should_buy_at_level(self, current_price: Decimal, grid_level: Decimal) -> bool:
        """Check if should buy at grid level.

        Args:
            current_price: Current price
            grid_level: Grid level price

        Returns:
            True if should buy
        """
        # Buy if price is near or below grid level
        threshold = grid_level * Decimal("1.001")  # 0.1% threshold
        return current_price <= threshold and grid_level not in self.active_orders

    def _should_sell_at_level(self, current_price: Decimal, grid_level: Decimal) -> bool:
        """Check if should sell at grid level.

        Args:
            current_price: Current price
            grid_level: Grid level price

        Returns:
            True if should sell
        """
        # Sell if price is near or above grid level
        threshold = grid_level * Decimal("0.999")  # 0.1% threshold
        return current_price >= threshold and grid_level not in self.active_orders

    def _calculate_grid_quantity(self, price: Decimal) -> Decimal:
        """Calculate quantity for grid order.

        Args:
            price: Order price

        Returns:
            Order quantity
        """
        position_size_usd = Decimal(str(self.get_parameter("position_size_usd")))
        quantity = position_size_usd / price
        return quantity

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
            metadata={"strategy": "grid"}
        )

    def mark_order_placed(self, price: Decimal, order_id: str):
        """Mark that an order was placed at a grid level.

        Args:
            price: Grid price
            order_id: Order ID
        """
        self.active_orders[price] = order_id

    def mark_order_filled(self, price: Decimal):
        """Mark that an order at a grid level was filled.

        Args:
            price: Grid price
        """
        if price in self.active_orders:
            del self.active_orders[price]
