"""Base strategy class for all trading strategies."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """Trading signal."""
    signal_type: SignalType
    symbol: str
    price: Decimal
    quantity: Decimal
    timestamp: datetime
    confidence: float = 1.0
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(
        self,
        name: str,
        symbol: str,
        parameters: Optional[Dict] = None
    ):
        """Initialize strategy.

        Args:
            name: Strategy name
            symbol: Trading pair symbol
            parameters: Strategy parameters
        """
        self.name = name
        self.symbol = symbol
        self.parameters = parameters or {}

        # State
        self.is_active = False
        self.last_signal: Optional[Signal] = None
        self.signals_history: List[Signal] = []

        logger.info(f"Initialized strategy: {self.name} for {self.symbol}")

    @abstractmethod
    def generate_signal(self, market_data: pd.DataFrame) -> Signal:
        """Generate trading signal based on market data.

        Args:
            market_data: DataFrame with market data (OHLCV)

        Returns:
            Trading signal
        """
        pass

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added indicators
        """
        pass

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate market data has required columns.

        Args:
            df: Market data DataFrame

        Returns:
            True if data is valid
        """
        required_columns = ["open", "high", "low", "close", "volume", "timestamp"]

        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False

        if df.empty:
            logger.warning("Empty DataFrame provided")
            return False

        return True

    def record_signal(self, signal: Signal):
        """Record a generated signal.

        Args:
            signal: Trading signal to record
        """
        self.last_signal = signal
        self.signals_history.append(signal)

        # Keep only last 1000 signals
        if len(self.signals_history) > 1000:
            self.signals_history = self.signals_history[-1000:]

        logger.info(
            f"[{self.name}] Signal: {signal.signal_type.value} "
            f"{signal.symbol} @ {signal.price} (qty: {signal.quantity})"
        )

    def get_signal_history(self, limit: int = 100) -> List[Signal]:
        """Get recent signal history.

        Args:
            limit: Maximum number of signals to return

        Returns:
            List of recent signals
        """
        return self.signals_history[-limit:]

    def start(self):
        """Start the strategy."""
        self.is_active = True
        logger.info(f"Strategy {self.name} started")

    def stop(self):
        """Stop the strategy."""
        self.is_active = False
        logger.info(f"Strategy {self.name} stopped")

    def get_parameter(self, key: str, default=None):
        """Get strategy parameter.

        Args:
            key: Parameter key
            default: Default value if not found

        Returns:
            Parameter value
        """
        return self.parameters.get(key, default)

    def set_parameter(self, key: str, value):
        """Set strategy parameter.

        Args:
            key: Parameter key
            value: Parameter value
        """
        self.parameters[key] = value
        logger.debug(f"Set parameter {key}={value} for {self.name}")

    def get_state(self) -> Dict:
        """Get strategy state.

        Returns:
            Dictionary with strategy state
        """
        return {
            "name": self.name,
            "symbol": self.symbol,
            "is_active": self.is_active,
            "parameters": self.parameters,
            "last_signal": {
                "type": self.last_signal.signal_type.value,
                "price": float(self.last_signal.price),
                "quantity": float(self.last_signal.quantity),
                "timestamp": self.last_signal.timestamp.isoformat()
            } if self.last_signal else None,
            "signals_count": len(self.signals_history)
        }

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', symbol='{self.symbol}')>"
