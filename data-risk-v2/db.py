import logging
import os
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
                "Add it to your .env file or Render dashboard."
            )
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
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

    sql = text("""
        SELECT date, open, high, low, close, volume
        FROM   ohlcv_cache
        WHERE  symbol   = :symbol
          AND  exchange = :exchange
          AND  date     BETWEEN :start AND :end
        ORDER  BY date
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(
                sql, conn,
                params={"symbol": symbol, "exchange": exchange, "start": start, "end": end},
                parse_dates=["date"],
                index_col="date",
            )
        logger.info("Daily cache hit: %d rows for %s/%s", len(df), symbol, exchange)
        return df
    except Exception as exc:
        logger.error("Daily cache read failed for %s: %s", symbol, exc)
        return pd.DataFrame()


def write_cache(
    symbol: str,
    exchange: str,
    df: pd.DataFrame,
) -> None:

    if df is None or df.empty:
        return

    records = [
        {
            "symbol":   symbol,
            "exchange": exchange,
            "date":     str(idx.date()) if hasattr(idx, "date") else str(idx),
            "open":     float(row["open"]),
            "high":     float(row["high"]),
            "low":      float(row["low"]),
            "close":    float(row["close"]),
            "volume":   int(row["volume"]),
        }
        for idx, row in df.iterrows()
    ]
    if not records:
        return

    sql = text("""
        INSERT INTO ohlcv_cache (symbol, exchange, date, open, high, low, close, volume)
        VALUES (:symbol, :exchange, :date, :open, :high, :low, :close, :volume)
        ON CONFLICT (symbol, exchange, date) DO NOTHING
    """)
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(sql, records)
        logger.info("Cached %d daily rows for %s/%s", len(records), symbol, exchange)
    except Exception as exc:
        logger.error("Daily cache write failed for %s: %s", symbol, exc)



def read_intraday_cache(
    symbol: str,
    exchange: str,
    resolution: str,
    start: str,
    end: str,
) -> pd.DataFrame:
   
    sql = text("""
        SELECT timestamp, open, high, low, close, volume
        FROM   ohlcv_intraday_cache
        WHERE  symbol     = :symbol
          AND  exchange   = :exchange
          AND  resolution = :resolution
          AND  timestamp  BETWEEN :start AND :end
        ORDER  BY timestamp
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(
                sql, conn,
                params={
                    "symbol": symbol, "exchange": exchange,
                    "resolution": resolution,
                    "start": start + " 00:00:00",
                    "end":   end   + " 23:59:59",
                },
                parse_dates=["timestamp"],
                index_col="timestamp",
            )
        df.index.name = "date"
        logger.info(
            "Intraday cache hit: %d rows for %s/%s @%s",
            len(df), symbol, exchange, resolution,
        )
        return df
    except Exception as exc:
        logger.error("Intraday cache read failed for %s: %s", symbol, exc)
        return pd.DataFrame()


def write_intraday_cache(
    symbol: str,
    exchange: str,
    resolution: str,
    df: pd.DataFrame,
) -> None:

    if df is None or df.empty:
        return

    records = [
        {
            "symbol":     symbol,
            "exchange":   exchange,
            "resolution": resolution,
            "timestamp":  str(idx) if not hasattr(idx, "isoformat") else idx.isoformat(),
            "open":       float(row["open"]),
            "high":       float(row["high"]),
            "low":        float(row["low"]),
            "close":      float(row["close"]),
            "volume":     int(row["volume"]),
        }
        for idx, row in df.iterrows()
    ]
    if not records:
        return

    sql = text("""
        INSERT INTO ohlcv_intraday_cache
            (symbol, exchange, resolution, timestamp, open, high, low, close, volume)
        VALUES
            (:symbol, :exchange, :resolution, :timestamp, :open, :high, :low, :close, :volume)
        ON CONFLICT (symbol, exchange, resolution, timestamp) DO NOTHING
    """)
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(sql, records)
        logger.info(
            "Cached %d intraday rows for %s/%s @%s",
            len(records), symbol, exchange, resolution,
        )
    except Exception as exc:
        logger.error("Intraday cache write failed for %s: %s", symbol, exc)



def save_fyers_credentials(
    user_id: str,
    app_id: str,
    access_token: str,
) -> None:
   
    sql = text("""
        UPDATE public.profiles
        SET    fyers_app_id       = :app_id,
               fyers_token        = :token,
               fyers_connected_at = NOW()
        WHERE  id = :uid
    """)
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            result = conn.execute(sql, {"app_id": app_id, "token": access_token, "uid": user_id})
            if result.rowcount == 0:
                logger.warning("save_fyers_credentials: no profile found for user_id=%s", user_id)
            else:
                logger.info("Fyers credentials saved for user_id=%s", user_id)
    except Exception as exc:
        logger.error("save_fyers_credentials failed for user_id=%s: %s", user_id, exc)
        raise


def get_fyers_credentials(user_id: str) -> dict | None:

    sql = text("""
        SELECT fyers_app_id, fyers_token, fyers_connected_at
        FROM   public.profiles
        WHERE  id = :uid
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(sql, {"uid": user_id}).fetchone()

        if not row or not row.fyers_token:
            return None

        return {
            "app_id":       row.fyers_app_id,
            "access_token": row.fyers_token,
            "connected_at": str(row.fyers_connected_at),
        }
    except Exception as exc:
        logger.error("get_fyers_credentials failed for user_id=%s: %s", user_id, exc)
        return None


def clear_fyers_credentials(user_id: str) -> None:
  
    sql = text("""
        UPDATE public.profiles
        SET    fyers_app_id       = NULL,
               fyers_token        = NULL,
               fyers_connected_at = NULL
        WHERE  id = :uid
    """)
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(sql, {"uid": user_id})
        logger.info("Fyers credentials cleared for user_id=%s", user_id)
    except Exception as exc:
        logger.error("clear_fyers_credentials failed: %s", exc)
