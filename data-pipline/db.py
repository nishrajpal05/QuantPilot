

import logging
import os
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Add it to your .env or Render dashboard."
            )
   
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        _engine = create_engine(
            database_url,
            pool_pre_ping=True,      # detect stale connections
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 10},
        )
        logger.info("Database engine created")
    return _engine



def read_cache(
    symbol: str,
    exchange: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """
    Read cached OHLCV rows from Supabase for the given symbol/exchange/range.

    Returns a DataFrame with DatetimeIndex and lowercase columns
    (open, high, low, close, volume), or an empty DataFrame if nothing cached.
    """
    sql = text(
        """
        SELECT date, open, high, low, close, volume
        FROM   ohlcv_cache
        WHERE  symbol   = :symbol
          AND  exchange = :exchange
          AND  date     BETWEEN :start AND :end
        ORDER  BY date
        """
    )
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(
                sql,
                conn,
                params={"symbol": symbol, "exchange": exchange, "start": start, "end": end},
                parse_dates=["date"],
                index_col="date",
            )
        logger.info(
            "Cache hit: %d rows for %s/%s  %s → %s", len(df), symbol, exchange, start, end
        )
        return df
    except Exception as exc:
        logger.error("Cache read failed for %s: %s", symbol, exc)
        return pd.DataFrame()


def write_cache(
    symbol: str,
    exchange: str,
    df: pd.DataFrame,
) -> None:
    """
    Upsert OHLCV rows into the cache table.
    Uses INSERT … ON CONFLICT DO NOTHING so existing rows are never overwritten.

    Args:
        symbol:   Ticker symbol, e.g. 'RELIANCE'
        exchange: 'NSE' or 'BSE'
        df:       OHLCV DataFrame with DatetimeIndex and lowercase columns
    """
    if df is None or df.empty:
        logger.info("write_cache called with empty DataFrame — skipping")
        return

    records = []
    for date_idx, row in df.iterrows():
        records.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "date": str(date_idx.date()) if hasattr(date_idx, "date") else str(date_idx),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }
        )

    if not records:
        return

    sql = text(
        """
        INSERT INTO ohlcv_cache (symbol, exchange, date, open, high, low, close, volume)
        VALUES (:symbol, :exchange, :date, :open, :high, :low, :close, :volume)
        ON CONFLICT (symbol, exchange, date) DO NOTHING
        """
    )
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(sql, records)
        logger.info("Cached %d rows for %s/%s", len(records), symbol, exchange)
    except Exception as exc:
        # Cache write failure is non-fatal — backtest can still proceed
        logger.error("Cache write failed for %s: %s", symbol, exc)
