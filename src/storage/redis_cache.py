"""Redis cache for real-time market state."""

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional
import redis
from redis.exceptions import RedisError

from ..config import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager for market state."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize Redis cache.

        Args:
            redis_client: Custom Redis client (uses settings if None)
        """
        if redis_client:
            self.redis = redis_client
        else:
            settings = get_settings()
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )

        # Test connection
        try:
            self.redis.ping()
            logger.info("Redis connection established")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def set_price(self, symbol: str, price: float, ttl: int = 60):
        """Cache latest price for a symbol.

        Args:
            symbol: Trading pair symbol
            price: Current price
            ttl: Time to live in seconds
        """
        key = f"price:{symbol}"
        try:
            self.redis.setex(key, ttl, str(price))
        except RedisError as e:
            logger.error(f"Failed to cache price for {symbol}: {e}")

    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Cached price or None
        """
        key = f"price:{symbol}"
        try:
            price_str = self.redis.get(key)
            return float(price_str) if price_str else None
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to retrieve price for {symbol}: {e}")
            return None

    def set_orderbook(self, symbol: str, orderbook: Dict, ttl: int = 30):
        """Cache order book data.

        Args:
            symbol: Trading pair symbol
            orderbook: Order book data (bids, asks)
            ttl: Time to live in seconds
        """
        key = f"orderbook:{symbol}"
        try:
            self.redis.setex(key, ttl, json.dumps(orderbook))
        except RedisError as e:
            logger.error(f"Failed to cache orderbook for {symbol}: {e}")

    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """Get cached order book data.

        Args:
            symbol: Trading pair symbol

        Returns:
            Order book data or None
        """
        key = f"orderbook:{symbol}"
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve orderbook for {symbol}: {e}")
            return None

    def set_ticker(self, symbol: str, ticker: Dict, ttl: int = 60):
        """Cache ticker data.

        Args:
            symbol: Trading pair symbol
            ticker: Ticker data
            ttl: Time to live in seconds
        """
        key = f"ticker:{symbol}"
        try:
            self.redis.setex(key, ttl, json.dumps(ticker))
        except RedisError as e:
            logger.error(f"Failed to cache ticker for {symbol}: {e}")

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get cached ticker data.

        Args:
            symbol: Trading pair symbol

        Returns:
            Ticker data or None
        """
        key = f"ticker:{symbol}"
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve ticker for {symbol}: {e}")
            return None

    def add_trade(self, symbol: str, trade: Dict, max_trades: int = 1000):
        """Add trade to symbol's trade list.

        Args:
            symbol: Trading pair symbol
            trade: Trade data
            max_trades: Maximum trades to keep in list
        """
        key = f"trades:{symbol}"
        try:
            # Add to list
            self.redis.lpush(key, json.dumps(trade))
            # Trim to max size
            self.redis.ltrim(key, 0, max_trades - 1)
            # Set expiry
            self.redis.expire(key, 3600)  # 1 hour
        except RedisError as e:
            logger.error(f"Failed to add trade for {symbol}: {e}")

    def get_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades for a symbol.

        Args:
            symbol: Trading pair symbol
            limit: Maximum number of trades to return

        Returns:
            List of recent trades
        """
        key = f"trades:{symbol}"
        try:
            trades_json = self.redis.lrange(key, 0, limit - 1)
            return [json.loads(t) for t in trades_json]
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve trades for {symbol}: {e}")
            return []

    def set_position(self, symbol: str, position: Dict):
        """Cache current position for a symbol.

        Args:
            symbol: Trading pair symbol
            position: Position data
        """
        key = f"position:{symbol}"
        try:
            self.redis.set(key, json.dumps(position))
        except RedisError as e:
            logger.error(f"Failed to cache position for {symbol}: {e}")

    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get cached position for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Position data or None
        """
        key = f"position:{symbol}"
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve position for {symbol}: {e}")
            return None

    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all cached positions.

        Returns:
            Dictionary of symbol -> position data
        """
        positions = {}
        try:
            keys = self.redis.keys("position:*")
            for key in keys:
                symbol = key.split(":", 1)[1]
                data = self.redis.get(key)
                if data:
                    positions[symbol] = json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve all positions: {e}")
        return positions

    def set_risk_metrics(self, metrics: Dict, ttl: int = 300):
        """Cache risk metrics.

        Args:
            metrics: Risk metrics data
            ttl: Time to live in seconds
        """
        key = "risk:metrics"
        try:
            self.redis.setex(key, ttl, json.dumps(metrics))
        except RedisError as e:
            logger.error(f"Failed to cache risk metrics: {e}")

    def get_risk_metrics(self) -> Optional[Dict]:
        """Get cached risk metrics.

        Returns:
            Risk metrics or None
        """
        key = "risk:metrics"
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve risk metrics: {e}")
            return None

    def set_circuit_breaker(self, is_active: bool, reason: str = ""):
        """Set circuit breaker state.

        Args:
            is_active: Whether circuit breaker is active
            reason: Reason for activation
        """
        key = "circuit_breaker"
        data = {"active": is_active, "reason": reason}
        try:
            self.redis.set(key, json.dumps(data))
        except RedisError as e:
            logger.error(f"Failed to set circuit breaker state: {e}")

    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is active.

        Returns:
            True if circuit breaker is active
        """
        key = "circuit_breaker"
        try:
            data = self.redis.get(key)
            if data:
                state = json.loads(data)
                return state.get("active", False)
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to check circuit breaker: {e}")
        return False

    def clear_cache(self, pattern: str = "*"):
        """Clear cache entries matching pattern.

        Args:
            pattern: Redis key pattern (default: all)
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
        except RedisError as e:
            logger.error(f"Failed to clear cache: {e}")

    def health_check(self) -> bool:
        """Check Redis health.

        Returns:
            True if Redis is healthy
        """
        try:
            return self.redis.ping()
        except RedisError:
            return False
