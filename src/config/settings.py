"""Application settings and configuration."""

from functools import lru_cache
from typing import List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Binance API
    binance_api_key: str = Field(..., description="Binance API key")
    binance_api_secret: str = Field(..., description="Binance API secret")
    binance_testnet: bool = Field(default=True, description="Use Binance testnet")

    # Trading Configuration
    trading_pairs: str = Field(default="BTCUSDT,ETHUSDT", description="Comma-separated trading pairs")

    @property
    def trading_pairs_list(self) -> List[str]:
        """Parse trading pairs into a list."""
        return [pair.strip() for pair in self.trading_pairs.split(",")]

    # Risk Parameters
    max_position_size_usd: float = Field(default=1000.0, description="Maximum position size in USD")
    max_total_exposure_usd: float = Field(default=5000.0, description="Maximum total exposure in USD")
    max_daily_loss_usd: float = Field(default=200.0, description="Maximum daily loss in USD")
    circuit_breaker_loss_percent: float = Field(default=5.0, description="Circuit breaker loss percentage")

    # Order Configuration
    default_order_timeout: int = Field(default=60, description="Default order timeout in seconds")
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts for failed orders")

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str | None = Field(default=None, description="Redis password")

    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="binance_bot", description="PostgreSQL database name")
    postgres_user: str = Field(default="bot_user", description="PostgreSQL user")
    postgres_password: str = Field(..., description="PostgreSQL password")

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Telegram Configuration
    telegram_bot_token: str | None = Field(default=None, description="Telegram bot token")
    telegram_chat_id: str | None = Field(default=None, description="Telegram chat ID")

    @property
    def telegram_enabled(self) -> bool:
        """Check if Telegram alerts are enabled."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    # Monitoring
    prometheus_port: int = Field(default=8000, description="Prometheus metrics port")

    # Application
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment name")

    # WebSocket Configuration
    ws_reconnect_delay: int = Field(default=5, description="WebSocket reconnect delay in seconds")
    ws_ping_interval: int = Field(default=20, description="WebSocket ping interval in seconds")

    # Data Storage
    data_dir: str = Field(default="./data", description="Data directory for Parquet files")

    @validator("circuit_breaker_loss_percent")
    def validate_circuit_breaker(cls, v):
        """Validate circuit breaker percentage."""
        if v <= 0 or v > 100:
            raise ValueError("Circuit breaker loss percent must be between 0 and 100")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
