"""Trend following strategy using moving averages and momentum."""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, Signal, SignalType

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """Conservative trend following strategy."""

    def __init__(
        self,
        symbol: str,
        fast_ma_period: int = 9,
        slow_ma_period: int = 21,
        rsi_period: int = 14,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
        position_size_usd: float = 500.0,
        **kwargs
    ):
        """Initialize trend following strategy.

        Args:
            symbol: Trading pair symbol
            fast_ma_period: Fast moving average period
            slow_ma_period: Slow moving average period
            rsi_period: RSI calculation period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            position_size_usd: Position size in USD
        """
        parameters = {
            "fast_ma_period": fast_ma_period,
            "slow_ma_period": slow_ma_period,
            "rsi_period": rsi_period,
            "rsi_oversold": rsi_oversold,
            "rsi_overbought": rsi_overbought,
            "position_size_usd": position_size_usd,
            **kwargs
        }

        super().__init__(name="TrendFollowing", symbol=symbol, parameters=parameters)

        self.in_position = False
        self.entry_price: Optional[Decimal] = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators.

        Args:
            df: OHLCV DataFrame

        Returns:
            DataFrame with indicators
        """
        fast_period = self.get_parameter("fast_ma_period")
        slow_period = self.get_parameter("slow_ma_period")
        rsi_period = self.get_parameter("rsi_period")

        # Exponential Moving Averages
        df["ema_fast"] = df["close"].ewm(span=fast_period, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=slow_period, adjust=False).mean()

        # RSI
        df["rsi"] = self._calculate_rsi(df["close"], rsi_period)

        # MACD
        df["macd"], df["macd_signal"], df["macd_hist"] = self._calculate_macd(df["close"])

        # ATR for volatility
        df["atr"] = self._calculate_atr(df, period=14)

        # Trend strength
        df["trend_strength"] = (df["ema_fast"] - df["ema_slow"]) / df["ema_slow"] * 100

        return df

    def generate_signal(self, market_data: pd.DataFrame) -> Signal:
        """Generate trend following signal.

        Args:
            market_data: DataFrame with OHLCV data

        Returns:
            Trading signal
        """
        if not self.validate_data(market_data):
            return self._hold_signal(market_data)

        # Calculate indicators
        df = self.calculate_indicators(market_data.copy())

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        current_price = Decimal(str(latest["close"]))
        timestamp = latest["timestamp"]

        # Generate signal based on indicators
        if self._should_buy(latest, prev):
            quantity = self._calculate_position_size(current_price)
            confidence = self._calculate_confidence(latest, "buy")

            signal = Signal(
                signal_type=SignalType.BUY,
                symbol=self.symbol,
                price=current_price,
                quantity=quantity,
                timestamp=timestamp,
                confidence=confidence,
                metadata={
                    "strategy": "trend_following",
                    "ema_fast": float(latest["ema_fast"]),
                    "ema_slow": float(latest["ema_slow"]),
                    "rsi": float(latest["rsi"]),
                    "macd_hist": float(latest["macd_hist"]),
                    "trend_strength": float(latest["trend_strength"])
                }
            )

        elif self._should_sell(latest, prev):
            quantity = self._calculate_position_size(current_price)
            confidence = self._calculate_confidence(latest, "sell")

            signal = Signal(
                signal_type=SignalType.SELL,
                symbol=self.symbol,
                price=current_price,
                quantity=quantity,
                timestamp=timestamp,
                confidence=confidence,
                metadata={
                    "strategy": "trend_following",
                    "ema_fast": float(latest["ema_fast"]),
                    "ema_slow": float(latest["ema_slow"]),
                    "rsi": float(latest["rsi"]),
                    "macd_hist": float(latest["macd_hist"]),
                    "trend_strength": float(latest["trend_strength"])
                }
            )

        else:
            signal = self._hold_signal(market_data)

        self.record_signal(signal)
        return signal

    def _should_buy(self, latest: pd.Series, prev: pd.Series) -> bool:
        """Check if should generate BUY signal.

        Args:
            latest: Latest candle data
            prev: Previous candle data

        Returns:
            True if should buy
        """
        rsi_oversold = self.get_parameter("rsi_oversold")

        # Don't buy if already in position
        if self.in_position:
            return False

        # Conditions for BUY:
        # 1. Fast EMA crosses above Slow EMA (golden cross)
        golden_cross = (
            latest["ema_fast"] > latest["ema_slow"] and
            prev["ema_fast"] <= prev["ema_slow"]
        )

        # 2. RSI is not overbought (gives room to grow)
        rsi_ok = latest["rsi"] < 70 and latest["rsi"] > rsi_oversold

        # 3. MACD histogram turning positive
        macd_positive = latest["macd_hist"] > 0 and latest["macd_hist"] > prev["macd_hist"]

        # 4. Upward trend
        upward_trend = latest["trend_strength"] > 0

        # Conservative approach: require multiple confirmations
        confirmations = sum([
            golden_cross or (latest["ema_fast"] > latest["ema_slow"] and upward_trend),
            rsi_ok,
            macd_positive,
        ])

        return confirmations >= 2

    def _should_sell(self, latest: pd.Series, prev: pd.Series) -> bool:
        """Check if should generate SELL signal.

        Args:
            latest: Latest candle data
            prev: Previous candle data

        Returns:
            True if should sell
        """
        rsi_overbought = self.get_parameter("rsi_overbought")

        # Only sell if in position
        if not self.in_position:
            return False

        # Conditions for SELL:
        # 1. Fast EMA crosses below Slow EMA (death cross)
        death_cross = (
            latest["ema_fast"] < latest["ema_slow"] and
            prev["ema_fast"] >= prev["ema_slow"]
        )

        # 2. RSI overbought
        rsi_overbought_signal = latest["rsi"] > rsi_overbought

        # 3. MACD histogram turning negative
        macd_negative = latest["macd_hist"] < 0 and latest["macd_hist"] < prev["macd_hist"]

        # 4. Downward trend
        downward_trend = latest["trend_strength"] < -1

        # Take profit or cut loss
        profit_target_hit = False
        stop_loss_hit = False

        if self.entry_price:
            current_price = Decimal(str(latest["close"]))
            pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100

            # Take profit at 5%
            profit_target_hit = pnl_percent >= Decimal("5")

            # Stop loss at -2%
            stop_loss_hit = pnl_percent <= Decimal("-2")

        # Sell if strong negative signals or risk management
        return (
            death_cross or
            (macd_negative and (rsi_overbought_signal or downward_trend)) or
            profit_target_hit or
            stop_loss_hit
        )

    def _calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate position size.

        Args:
            price: Current price

        Returns:
            Quantity to trade
        """
        position_size_usd = Decimal(str(self.get_parameter("position_size_usd")))
        quantity = position_size_usd / price
        return quantity

    def _calculate_confidence(self, latest: pd.Series, signal_type: str) -> float:
        """Calculate signal confidence score.

        Args:
            latest: Latest candle data
            signal_type: "buy" or "sell"

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence

        # Adjust based on trend strength
        trend_strength = abs(float(latest["trend_strength"]))
        confidence += min(trend_strength / 100, 0.2)  # Max +0.2

        # Adjust based on MACD histogram
        macd_hist = abs(float(latest["macd_hist"]))
        confidence += min(macd_hist / 100, 0.15)  # Max +0.15

        # Adjust based on RSI
        rsi = float(latest["rsi"])
        if signal_type == "buy" and rsi < 50:
            confidence += 0.15
        elif signal_type == "sell" and rsi > 50:
            confidence += 0.15

        return min(confidence, 1.0)

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator.

        Args:
            prices: Price series
            period: RSI period

        Returns:
            RSI series
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple:
        """Calculate MACD indicator.

        Args:
            prices: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            Tuple of (macd, signal, histogram)
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal

        return macd, macd_signal, macd_hist

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range.

        Args:
            df: OHLCV DataFrame
            period: ATR period

        Returns:
            ATR series
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

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
            metadata={"strategy": "trend_following"}
        )

    def set_position_status(self, in_position: bool, entry_price: Optional[Decimal] = None):
        """Update position status.

        Args:
            in_position: Whether currently in a position
            entry_price: Entry price if in position
        """
        self.in_position = in_position
        self.entry_price = entry_price

        if in_position:
            logger.info(f"Position opened at {entry_price}")
        else:
            logger.info("Position closed")
