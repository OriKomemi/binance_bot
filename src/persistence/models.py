"""Database models for persistence."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Enum, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class OrderSide(enum.Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(enum.Enum):
    """Order type enumeration."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"


class OrderStatus(enum.Enum):
    """Order status enumeration."""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Order(Base):
    """Order record."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)
    client_order_id = Column(String(100), unique=True, nullable=False)

    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, index=True)

    price = Column(Numeric(20, 8), nullable=True)
    quantity = Column(Numeric(20, 8), nullable=False)
    executed_qty = Column(Numeric(20, 8), default=0)
    cumulative_quote_qty = Column(Numeric(20, 8), default=0)

    time_in_force = Column(String(10), default="GTC")
    stop_price = Column(Numeric(20, 8), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    transact_time = Column(DateTime, nullable=True)

    strategy_name = Column(String(100), nullable=True, index=True)
    notes = Column(String(500), nullable=True)

    # Relationships
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_order_symbol_status", "symbol", "status"),
        Index("idx_order_created_at", "created_at"),
    )

    def __repr__(self):
        return (
            f"<Order(id={self.id}, order_id='{self.order_id}', "
            f"symbol='{self.symbol}', side={self.side.value}, status={self.status.value})>"
        )


class Trade(Base):
    """Trade (fill) record."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(100), unique=True, nullable=False, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order = relationship("Order", back_populates="trades")

    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)

    price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    quote_qty = Column(Numeric(20, 8), nullable=False)

    commission = Column(Numeric(20, 8), default=0)
    commission_asset = Column(String(10), nullable=True)

    is_buyer = Column(Boolean, nullable=False)
    is_maker = Column(Boolean, nullable=False)

    trade_time = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_trade_symbol_time", "symbol", "trade_time"),
    )

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, trade_id='{self.trade_id}', "
            f"symbol='{self.symbol}', price={self.price}, qty={self.quantity})>"
        )


class Position(Base):
    """Position record."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)

    quantity = Column(Numeric(20, 8), default=0, nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=True)
    current_price = Column(Numeric(20, 8), nullable=True)

    realized_pnl = Column(Numeric(20, 8), default=0)
    unrealized_pnl = Column(Numeric(20, 8), default=0)

    total_buy_qty = Column(Numeric(20, 8), default=0)
    total_sell_qty = Column(Numeric(20, 8), default=0)
    total_buy_value = Column(Numeric(20, 8), default=0)
    total_sell_value = Column(Numeric(20, 8), default=0)

    opened_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    is_open = Column(Boolean, default=True, nullable=False, index=True)

    strategy_name = Column(String(100), nullable=True, index=True)
    notes = Column(String(500), nullable=True)

    def __repr__(self):
        return (
            f"<Position(id={self.id}, symbol='{self.symbol}', "
            f"qty={self.quantity}, pnl={self.realized_pnl})>"
        )


class PnLRecord(Base):
    """Profit and Loss record."""

    __tablename__ = "pnl_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)

    date = Column(DateTime, nullable=False, index=True)
    strategy_name = Column(String(100), nullable=True, index=True)

    realized_pnl = Column(Numeric(20, 8), default=0)
    unrealized_pnl = Column(Numeric(20, 8), default=0)
    total_pnl = Column(Numeric(20, 8), default=0)

    trading_volume = Column(Numeric(20, 8), default=0)
    num_trades = Column(Integer, default=0)
    num_winning_trades = Column(Integer, default=0)
    num_losing_trades = Column(Integer, default=0)

    max_drawdown = Column(Numeric(10, 4), default=0)
    win_rate = Column(Numeric(5, 4), default=0)

    fees_paid = Column(Numeric(20, 8), default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_pnl_date_symbol", "date", "symbol"),
        Index("idx_pnl_strategy", "strategy_name", "date"),
    )

    def __repr__(self):
        return (
            f"<PnLRecord(id={self.id}, symbol='{self.symbol}', "
            f"date={self.date.date()}, pnl={self.total_pnl})>"
        )
