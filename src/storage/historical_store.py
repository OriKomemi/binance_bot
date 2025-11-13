"""Historical data storage using Parquet and PostgreSQL."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import get_settings

logger = logging.getLogger(__name__)


class HistoricalStore:
    """Manager for historical market data storage."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize historical store.

        Args:
            data_dir: Directory for Parquet files (uses settings if None)
        """
        settings = get_settings()
        self.data_dir = Path(data_dir or settings.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Historical store initialized at {self.data_dir}")

    def _get_file_path(self, symbol: str, data_type: str, date: datetime) -> Path:
        """Get file path for data storage.

        Args:
            symbol: Trading pair symbol
            data_type: Type of data (klines, trades, etc.)
            date: Date for partitioning

        Returns:
            Path to Parquet file
        """
        # Partition by year/month/day
        year_month = date.strftime("%Y-%m")
        day = date.strftime("%d")

        file_path = self.data_dir / data_type / symbol / year_month / f"{day}.parquet"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path

    def save_klines(self, symbol: str, df: pd.DataFrame, date: Optional[datetime] = None):
        """Save kline data to Parquet.

        Args:
            symbol: Trading pair symbol
            df: DataFrame with kline data
            date: Date for partitioning (uses first timestamp if None)
        """
        if df.empty:
            logger.warning(f"Empty DataFrame for {symbol}, skipping save")
            return

        # Use first timestamp for partitioning if date not provided
        if date is None:
            date = df["timestamp"].iloc[0]

        file_path = self._get_file_path(symbol, "klines", date)

        try:
            # Read existing data if file exists
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                # Combine and remove duplicates
                df = pd.concat([existing_df, df]).drop_duplicates(
                    subset=["timestamp"], keep="last"
                ).sort_values("timestamp")

            # Write to Parquet
            df.to_parquet(
                file_path,
                engine="pyarrow",
                compression="snappy",
                index=False
            )

            logger.debug(f"Saved {len(df)} klines for {symbol} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save klines for {symbol}: {e}")

    def load_klines(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Load kline data from Parquet files.

        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with kline data
        """
        dfs = []

        # Iterate through date range
        current_date = start_date
        while current_date <= end_date:
            file_path = self._get_file_path(symbol, "klines", current_date)

            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    dfs.append(df)
                except Exception as e:
                    logger.error(f"Failed to load klines from {file_path}: {e}")

            # Move to next day
            current_date = current_date + pd.Timedelta(days=1)

        if not dfs:
            logger.warning(f"No kline data found for {symbol} between {start_date} and {end_date}")
            return pd.DataFrame()

        # Combine all data
        combined_df = pd.concat(dfs, ignore_index=True)

        # Filter by exact date range
        combined_df = combined_df[
            (combined_df["timestamp"] >= start_date) &
            (combined_df["timestamp"] <= end_date)
        ].sort_values("timestamp").reset_index(drop=True)

        logger.info(f"Loaded {len(combined_df)} klines for {symbol}")
        return combined_df

    def save_trades(self, symbol: str, df: pd.DataFrame, date: Optional[datetime] = None):
        """Save trade data to Parquet.

        Args:
            symbol: Trading pair symbol
            df: DataFrame with trade data
            date: Date for partitioning
        """
        if df.empty:
            logger.warning(f"Empty trade DataFrame for {symbol}, skipping save")
            return

        if date is None:
            date = df["timestamp"].iloc[0]

        file_path = self._get_file_path(symbol, "trades", date)

        try:
            # Read existing data if file exists
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                # Combine and remove duplicates based on trade_id
                df = pd.concat([existing_df, df]).drop_duplicates(
                    subset=["trade_id"], keep="last"
                ).sort_values("timestamp")

            # Write to Parquet
            df.to_parquet(
                file_path,
                engine="pyarrow",
                compression="snappy",
                index=False
            )

            logger.debug(f"Saved {len(df)} trades for {symbol} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save trades for {symbol}: {e}")

    def load_trades(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Load trade data from Parquet files.

        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with trade data
        """
        dfs = []

        current_date = start_date
        while current_date <= end_date:
            file_path = self._get_file_path(symbol, "trades", current_date)

            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    dfs.append(df)
                except Exception as e:
                    logger.error(f"Failed to load trades from {file_path}: {e}")

            current_date = current_date + pd.Timedelta(days=1)

        if not dfs:
            logger.warning(f"No trade data found for {symbol}")
            return pd.DataFrame()

        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = combined_df[
            (combined_df["timestamp"] >= start_date) &
            (combined_df["timestamp"] <= end_date)
        ].sort_values("timestamp").reset_index(drop=True)

        logger.info(f"Loaded {len(combined_df)} trades for {symbol}")
        return combined_df

    def get_latest_timestamp(self, symbol: str, data_type: str = "klines") -> Optional[datetime]:
        """Get the latest timestamp for stored data.

        Args:
            symbol: Trading pair symbol
            data_type: Type of data (klines, trades)

        Returns:
            Latest timestamp or None
        """
        base_path = self.data_dir / data_type / symbol

        if not base_path.exists():
            return None

        # Find all parquet files
        parquet_files = sorted(base_path.rglob("*.parquet"), reverse=True)

        for file_path in parquet_files:
            try:
                df = pd.read_parquet(file_path)
                if not df.empty and "timestamp" in df.columns:
                    return df["timestamp"].max()
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")

        return None

    def cleanup_old_data(self, days_to_keep: int = 90):
        """Remove data older than specified days.

        Args:
            days_to_keep: Number of days of data to keep
        """
        cutoff_date = datetime.now() - pd.Timedelta(days=days_to_keep)
        removed_count = 0

        for data_type in ["klines", "trades"]:
            type_path = self.data_dir / data_type

            if not type_path.exists():
                continue

            for parquet_file in type_path.rglob("*.parquet"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(parquet_file.stat().st_mtime)

                    if mtime < cutoff_date:
                        parquet_file.unlink()
                        removed_count += 1

                except Exception as e:
                    logger.error(f"Failed to remove {parquet_file}: {e}")

        logger.info(f"Cleaned up {removed_count} old data files")

    def get_storage_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        stats = {
            "total_size_mb": 0,
            "file_count": 0,
            "symbols": set()
        }

        for parquet_file in self.data_dir.rglob("*.parquet"):
            stats["file_count"] += 1
            stats["total_size_mb"] += parquet_file.stat().st_size / (1024 * 1024)

            # Extract symbol from path
            parts = parquet_file.parts
            if len(parts) >= 2:
                stats["symbols"].add(parts[-3])  # Symbol is 3 levels up from file

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        stats["symbols"] = sorted(stats["symbols"])

        return stats
