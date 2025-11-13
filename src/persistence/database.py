"""Database manager for persistence operations."""

import logging
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings
from .models import Base, Order, Trade, Position, PnLRecord, OrderStatus

logger = logging.getLogger(__name__)


class Database:
    """Database manager for trading bot persistence."""

    def __init__(self, connection_url: Optional[str] = None):
        """Initialize database connection.

        Args:
            connection_url: PostgreSQL connection URL (uses settings if None)
        """
        settings = get_settings()
        self.connection_url = connection_url or settings.postgres_url

        self.engine = create_engine(
            self.connection_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info("Database connection initialized")

    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager.

        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()

    # Order operations
    def create_order(self, order_data: Dict) -> Order:
        """Create a new order record.

        Args:
            order_data: Order information

        Returns:
            Created Order object
        """
        with self.get_session() as session:
            order = Order(**order_data)
            session.add(order)
            session.flush()
            session.refresh(order)
            logger.info(f"Created order: {order.order_id}")
            return order

    def update_order(self, order_id: str, update_data: Dict) -> Optional[Order]:
        """Update an existing order.

        Args:
            order_id: Order ID
            update_data: Fields to update

        Returns:
            Updated Order object or None
        """
        with self.get_session() as session:
            order = session.query(Order).filter_by(order_id=order_id).first()
            if order:
                for key, value in update_data.items():
                    setattr(order, key, value)
                order.updated_at = datetime.utcnow()
                session.flush()
                logger.info(f"Updated order: {order_id}")
                return order
            return None

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order object or None
        """
        with self.get_session() as session:
            return session.query(Order).filter_by(order_id=order_id).first()

    def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        strategy_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get orders with filters.

        Args:
            symbol: Filter by symbol
            status: Filter by status
            strategy_name: Filter by strategy
            limit: Maximum number of orders to return

        Returns:
            List of Order objects
        """
        with self.get_session() as session:
            query = session.query(Order)

            if symbol:
                query = query.filter_by(symbol=symbol)
            if status:
                query = query.filter_by(status=status)
            if strategy_name:
                query = query.filter_by(strategy_name=strategy_name)

            return query.order_by(Order.created_at.desc()).limit(limit).all()

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of open orders
        """
        return self.get_orders(
            symbol=symbol,
            status=OrderStatus.NEW,
            limit=1000
        )

    # Trade operations
    def create_trade(self, trade_data: Dict) -> Trade:
        """Create a new trade record.

        Args:
            trade_data: Trade information

        Returns:
            Created Trade object
        """
        with self.get_session() as session:
            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()
            session.refresh(trade)
            logger.info(f"Created trade: {trade.trade_id}")
            return trade

    def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Trade]:
        """Get trades with filters.

        Args:
            symbol: Filter by symbol
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of trades

        Returns:
            List of Trade objects
        """
        with self.get_session() as session:
            query = session.query(Trade)

            if symbol:
                query = query.filter_by(symbol=symbol)
            if start_date:
                query = query.filter(Trade.trade_time >= start_date)
            if end_date:
                query = query.filter(Trade.trade_time <= end_date)

            return query.order_by(Trade.trade_time.desc()).limit(limit).all()

    # Position operations
    def upsert_position(self, symbol: str, position_data: Dict) -> Position:
        """Create or update a position.

        Args:
            symbol: Trading pair symbol
            position_data: Position information

        Returns:
            Position object
        """
        with self.get_session() as session:
            position = session.query(Position).filter_by(symbol=symbol).first()

            if position:
                # Update existing position
                for key, value in position_data.items():
                    setattr(position, key, value)
                position.updated_at = datetime.utcnow()
            else:
                # Create new position
                position_data["symbol"] = symbol
                position = Position(**position_data)
                session.add(position)

            session.flush()
            session.refresh(position)
            return position

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Position object or None
        """
        with self.get_session() as session:
            return session.query(Position).filter_by(symbol=symbol).first()

    def get_all_positions(self, is_open: bool = True) -> List[Position]:
        """Get all positions.

        Args:
            is_open: Filter by open positions

        Returns:
            List of Position objects
        """
        with self.get_session() as session:
            query = session.query(Position).filter_by(is_open=is_open)
            return query.all()

    def close_position(self, symbol: str) -> Optional[Position]:
        """Close a position.

        Args:
            symbol: Trading pair symbol

        Returns:
            Closed Position object or None
        """
        with self.get_session() as session:
            position = session.query(Position).filter_by(symbol=symbol).first()
            if position:
                position.is_open = False
                position.closed_at = datetime.utcnow()
                session.flush()
                logger.info(f"Closed position for {symbol}")
                return position
            return None

    # PnL operations
    def create_pnl_record(self, pnl_data: Dict) -> PnLRecord:
        """Create a PnL record.

        Args:
            pnl_data: PnL information

        Returns:
            Created PnLRecord object
        """
        with self.get_session() as session:
            pnl_record = PnLRecord(**pnl_data)
            session.add(pnl_record)
            session.flush()
            session.refresh(pnl_record)
            return pnl_record

    def get_pnl_records(
        self,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PnLRecord]:
        """Get PnL records with filters.

        Args:
            symbol: Filter by symbol
            strategy_name: Filter by strategy
            start_date: Start date
            end_date: End date
            limit: Maximum records

        Returns:
            List of PnLRecord objects
        """
        with self.get_session() as session:
            query = session.query(PnLRecord)

            if symbol:
                query = query.filter_by(symbol=symbol)
            if strategy_name:
                query = query.filter_by(strategy_name=strategy_name)
            if start_date:
                query = query.filter(PnLRecord.date >= start_date)
            if end_date:
                query = query.filter(PnLRecord.date <= end_date)

            return query.order_by(PnLRecord.date.desc()).limit(limit).all()

    def get_total_pnl(
        self,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None
    ) -> Decimal:
        """Calculate total PnL.

        Args:
            symbol: Filter by symbol
            strategy_name: Filter by strategy

        Returns:
            Total PnL
        """
        with self.get_session() as session:
            query = session.query(func.sum(PnLRecord.total_pnl))

            if symbol:
                query = query.filter(PnLRecord.symbol == symbol)
            if strategy_name:
                query = query.filter(PnLRecord.strategy_name == strategy_name)

            result = query.scalar()
            return result or Decimal(0)

    def health_check(self) -> bool:
        """Check database health.

        Returns:
            True if database is healthy
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
