

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase all column names and keep only OHLCV columns."""
    df.columns = [c.lower() for c in df.columns]
    ohlcv = ["open", "high", "low", "close", "volume"]
    return df[ohlcv].copy()


def fetch_from_nsepy(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch OHLCV data using nsepy (official NSE data).
    Returns DataFrame with DatetimeIndex and lowercase columns.
    """
    try:
        import nsepy  # noqa: PLC0415 — optional dependency
    except ImportError:
        raise ImportError("nsepy is not installed. Run: pip install nsepy")

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    logger.info("nsepy fetch: %s  %s → %s", symbol, start, end)
    raw = nsepy.get_history(
        symbol=symbol,
        start=start_dt,
        end=end_dt,
    )

    if raw is None or raw.empty:
        raise ValueError(f"nsepy returned empty DataFrame for {symbol}")

    df = _normalise_columns(raw[["Open", "High", "Low", "Close", "Volume"]])
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df


def fetch_from_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch OHLCV data using yfinance (NSE suffix .NS).
    Returns DataFrame with DatetimeIndex and lowercase columns.
    """
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        raise ImportError("yfinance is not installed. Run: pip install yfinance")

    # Handle index symbols (e.g. "NIFTY 50" → "^NSEI")
    INDEX_MAP = {
        "NIFTY 50": "^NSEI",
        "NIFTY50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
    }
    ticker_symbol = INDEX_MAP.get(symbol.upper(), symbol + ".NS")

    logger.info("yfinance fetch: %s (%s)  %s → %s", symbol, ticker_symbol, start, end)
    raw = yf.download(ticker_symbol, start=start, end=end, progress=False, auto_adjust=True)

    if raw is None or raw.empty:
        raise ValueError(f"yfinance returned empty DataFrame for {ticker_symbol}")

    df = _normalise_columns(raw[["Open", "High", "Low", "Close", "Volume"]])
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df


def fetch_ohlcv(
    symbol: str,
    start: str,
    end: str,
    exchange: str = "NSE",
) -> pd.DataFrame:
   
    try:
        df = fetch_from_nsepy(symbol, start, end)
        if df.empty:
            raise ValueError("nsepy returned empty data")
        logger.info("nsepy success: %d rows for %s", len(df), symbol)
        return df
    except Exception as primary_exc:
        logger.warning(
            "nsepy failed for %s (%s), falling back to yfinance", symbol, primary_exc
        )
        try:
            df = fetch_from_yfinance(symbol, start, end)
            logger.info("yfinance success: %d rows for %s", len(df), symbol)
            return df
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Both data sources failed for {symbol}. "
                f"nsepy: {primary_exc} | yfinance: {fallback_exc}"
            ) from fallback_exc
