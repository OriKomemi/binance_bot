"""Risk management and position sizing."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from ..config import get_settings
from ..storage import RedisCache
from ..persistence import Database

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics container."""
    total_exposure_usd: Decimal
    max_position_size_usd: Decimal
    max_total_exposure_usd: Decimal
    daily_loss_usd: Decimal
    max_daily_loss_usd: Decimal
    circuit_breaker_active: bool
    circuit_breaker_reason: str
    positions_count: int


class RiskManager:
    """Risk manager for trade approval and position sizing."""

    def __init__(
        self,
        redis_cache: Optional[RedisCache] = None,
        database: Optional[Database] = None
    ):
        """Initialize risk manager.

        Args:
            redis_cache: Redis cache instance
            database: Database instance
        """
        self.settings = get_settings()
        self.redis = redis_cache or RedisCache()
        self.db = database or Database()

        # Risk parameters from settings
        self.max_position_size_usd = Decimal(str(self.settings.max_position_size_usd))
        self.max_total_exposure_usd = Decimal(str(self.settings.max_total_exposure_usd))
        self.max_daily_loss_usd = Decimal(str(self.settings.max_daily_loss_usd))
        self.circuit_breaker_threshold = Decimal(str(self.settings.circuit_breaker_loss_percent))

        logger.info("Risk manager initialized")

    def check_order_approval(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal
    ) -> Tuple[bool, str]:
        """Check if an order should be approved.

        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            price: Order price

        Returns:
            Tuple of (approved, reason)
        """
        # Check circuit breaker first
        if self.is_circuit_breaker_active():
            reason = self._get_circuit_breaker_reason()
            logger.warning(f"Order rejected: Circuit breaker active - {reason}")
            return False, f"Circuit breaker active: {reason}"

        # Calculate order value
        order_value_usd = quantity * price

        # Check individual position size for BUY orders
        if side.upper() == "BUY":
            if order_value_usd > self.max_position_size_usd:
                reason = (
                    f"Order value ${order_value_usd:.2f} exceeds "
                    f"max position size ${self.max_position_size_usd:.2f}"
                )
                logger.warning(f"Order rejected: {reason}")
                return False, reason

        # Check total exposure
        current_exposure = self.get_total_exposure()
        if side.upper() == "BUY":
            new_exposure = current_exposure + order_value_usd
            if new_exposure > self.max_total_exposure_usd:
                reason = (
                    f"New exposure ${new_exposure:.2f} would exceed "
                    f"max total exposure ${self.max_total_exposure_usd:.2f}"
                )
                logger.warning(f"Order rejected: {reason}")
                return False, reason

        # Check daily loss limits
        daily_loss = self.get_daily_loss()
        if daily_loss > self.max_daily_loss_usd:
            reason = (
                f"Daily loss ${daily_loss:.2f} exceeds "
                f"max daily loss ${self.max_daily_loss_usd:.2f}"
            )
            logger.warning(f"Order rejected: {reason}")
            self.activate_circuit_breaker(reason)
            return False, reason

        logger.info(f"Order approved: {symbol} {side} {quantity} @ {price}")
        return True, "Approved"

    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        risk_percent: Decimal = Decimal("0.01")
    ) -> Decimal:
        """Calculate appropriate position size based on risk.

        Args:
            symbol: Trading pair symbol
            price: Current price
            risk_percent: Risk per trade as decimal (default 1%)

        Returns:
            Recommended position size
        """
        # Calculate maximum position based on risk limit
        max_risk_amount = self.max_position_size_usd * risk_percent
        position_size = max_risk_amount / price

        # Ensure position doesn't exceed max position size
        max_quantity = self.max_position_size_usd / price
        position_size = min(position_size, max_quantity)

        # Check available exposure
        current_exposure = self.get_total_exposure()
        available_exposure = self.max_total_exposure_usd - current_exposure

        if available_exposure <= 0:
            logger.warning("No available exposure for new positions")
            return Decimal("0")

        # Limit position size by available exposure
        max_by_exposure = available_exposure / price
        position_size = min(position_size, max_by_exposure)

        logger.debug(
            f"Calculated position size for {symbol}: {position_size} "
            f"(price: {price}, risk: {risk_percent * 100}%)"
        )

        return position_size

    def get_total_exposure(self) -> Decimal:
        """Calculate total current exposure across all positions.

        Returns:
            Total exposure in USD
        """
        total_exposure = Decimal("0")

        try:
            positions = self.db.get_all_positions(is_open=True)

            for position in positions:
                if position.current_price and position.quantity:
                    exposure = Decimal(str(position.quantity)) * Decimal(str(position.current_price))
                    total_exposure += exposure

        except Exception as e:
            logger.error(f"Failed to calculate total exposure: {e}")

        return total_exposure

    def get_daily_loss(self) -> Decimal:
        """Calculate daily loss/gain.

        Returns:
            Daily PnL (negative for loss)
        """
        try:
            today = datetime.now().date()
            start_of_day = datetime.combine(today, datetime.min.time())

            pnl_records = self.db.get_pnl_records(
                start_date=start_of_day,
                limit=1000
            )

            total_pnl = sum(
                Decimal(str(record.total_pnl)) for record in pnl_records
            )

            # Negative PnL is a loss
            daily_loss = abs(total_pnl) if total_pnl < 0 else Decimal("0")

            return daily_loss

        except Exception as e:
            logger.error(f"Failed to calculate daily loss: {e}")
            return Decimal("0")

    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently active.

        Returns:
            True if circuit breaker is active
        """
        return self.redis.is_circuit_breaker_active()

    def activate_circuit_breaker(self, reason: str):
        """Activate circuit breaker to halt trading.

        Args:
            reason: Reason for activation
        """
        logger.critical(f"CIRCUIT BREAKER ACTIVATED: {reason}")
        self.redis.set_circuit_breaker(is_active=True, reason=reason)

    def deactivate_circuit_breaker(self):
        """Deactivate circuit breaker."""
        logger.info("Circuit breaker deactivated")
        self.redis.set_circuit_breaker(is_active=False, reason="")

    def _get_circuit_breaker_reason(self) -> str:
        """Get reason for circuit breaker activation.

        Returns:
            Circuit breaker reason
        """
        try:
            data = self.redis.redis.get("circuit_breaker")
            if data:
                import json
                state = json.loads(data)
                return state.get("reason", "Unknown")
        except Exception:
            pass
        return "Unknown"

    def update_position_risk(self, symbol: str, current_price: Decimal):
        """Update position risk metrics.

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
        """
        try:
            position = self.db.get_position(symbol)
            if not position or not position.is_open:
                return

            # Update current price
            quantity = Decimal(str(position.quantity))
            entry_price = Decimal(str(position.entry_price or 0))

            # Calculate unrealized PnL
            if quantity > 0:  # Long position
                unrealized_pnl = (current_price - entry_price) * quantity
            else:  # Short position (though we don't use shorts in spot)
                unrealized_pnl = (entry_price - current_price) * abs(quantity)

            # Update position
            self.db.upsert_position(symbol, {
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl
            })

        except Exception as e:
            logger.error(f"Failed to update position risk for {symbol}: {e}")

    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics.

        Returns:
            RiskMetrics object
        """
        total_exposure = self.get_total_exposure()
        daily_loss = self.get_daily_loss()
        circuit_breaker = self.is_circuit_breaker_active()
        reason = self._get_circuit_breaker_reason() if circuit_breaker else ""

        positions = self.db.get_all_positions(is_open=True)

        metrics = RiskMetrics(
            total_exposure_usd=total_exposure,
            max_position_size_usd=self.max_position_size_usd,
            max_total_exposure_usd=self.max_total_exposure_usd,
            daily_loss_usd=daily_loss,
            max_daily_loss_usd=self.max_daily_loss_usd,
            circuit_breaker_active=circuit_breaker,
            circuit_breaker_reason=reason,
            positions_count=len(positions)
        )

        # Cache metrics
        self.redis.set_risk_metrics({
            "total_exposure_usd": float(total_exposure),
            "daily_loss_usd": float(daily_loss),
            "circuit_breaker_active": circuit_breaker,
            "positions_count": len(positions),
            "updated_at": datetime.now().isoformat()
        })

        return metrics

    def check_daily_loss_circuit_breaker(self):
        """Check daily loss and trigger circuit breaker if needed."""
        daily_loss = self.get_daily_loss()
        loss_percent = (daily_loss / self.max_total_exposure_usd) * 100

        if loss_percent >= self.circuit_breaker_threshold:
            reason = (
                f"Daily loss {loss_percent:.2f}% exceeds threshold "
                f"{self.circuit_breaker_threshold:.2f}%"
            )
            self.activate_circuit_breaker(reason)
