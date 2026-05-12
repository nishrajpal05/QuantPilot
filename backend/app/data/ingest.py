import logging
import math
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase all column names and keep only OHLCV columns."""
    df = df.copy()
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    ohlcv = ["open", "high", "low", "close", "volume"]
    return df[ohlcv].copy()


def fetch_from_nsepy(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch OHLCV data using nsepy.
    Returns DataFrame with DatetimeIndex, lowercase columns, and attrs["data_source"]="nsepy".
    """
    try:
        import nsepy
    except ImportError:
        raise ImportError("nsepy is not installed. Run: pip install nsepy")

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    logger.info("nsepy fetch: %s %s to %s", symbol, start, end)
    raw = nsepy.get_history(symbol=symbol, start=start_dt, end=end_dt)

    if raw is None or raw.empty:
        raise ValueError(f"nsepy returned empty DataFrame for {symbol}")

    df = _normalise_columns(raw[["Open", "High", "Low", "Close", "Volume"]])
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df.attrs["data_source"] = "nsepy"
    return df


def fetch_from_yfinance(symbol: str, start: str, end: str, exchange: str = "NSE") -> pd.DataFrame:
    """
    Fetch OHLCV data using yfinance >= 1.0 (Ticker.history API).
    Returns DataFrame with DatetimeIndex (date-only), lowercase columns,
    and attrs["data_source"] = "yfinance".
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance is not installed. Run: pip install 'yfinance>=1.0'")

    index_map = {
        "NIFTY 50": "^NSEI",
        "NIFTY50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
    }
    clean_symbol = symbol.upper().strip()
    if clean_symbol in index_map:
        ticker_candidates = [index_map[clean_symbol]]
    elif exchange.upper() == "BSE":
        ticker_candidates = [clean_symbol if clean_symbol.endswith(".BO") else f"{clean_symbol}.BO"]
    else:
        ticker_candidates = [
            clean_symbol if clean_symbol.endswith(".NS") else f"{clean_symbol}.NS",
            clean_symbol,
        ]

    raw = None
    errors = []
    for ticker_symbol in ticker_candidates:
        logger.info("yfinance fetch (Ticker.history): %s (%s) %s to %s", symbol, ticker_symbol, start, end)
        try:
            ticker = yf.Ticker(ticker_symbol)
            candidate = ticker.history(
                start=start,
                end=end,
                auto_adjust=True,
                actions=False,
            )
            if candidate is not None and not candidate.empty:
                raw = candidate
                logger.info("yfinance got %d rows for %s", len(raw), ticker_symbol)
                break
            errors.append(f"{ticker_symbol}: empty")
        except Exception as exc:
            errors.append(f"{ticker_symbol}: {exc}")

    if raw is None or raw.empty:
        raise ValueError(f"yfinance returned no data for {symbol} ({'; '.join(errors)})")

    # yfinance 1.x returns timezone-aware index — normalise to date-only
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    raw.index = raw.index.normalize()  # strip time component

    # Normalise column names (Open/High/Low/Close/Volume → lowercase)
    df = _normalise_columns(raw)
    df.index.name = "date"
    df.attrs["data_source"] = "yfinance"
    return df


def fetch_ohlcv(
    symbol: str,
    start: str,
    end: str,
    exchange: str = "NSE",
) -> pd.DataFrame:
    """
    Fetch real OHLCV data: yfinance first (reliable locally), nsepy as fallback.

    Raises RuntimeError with a clear message if both fail.
    Never silently falls back to fake/sample data.
    Set QP_OFFLINE_MODE=1 ONLY for explicit offline testing — clearly labelled.
    """
    # Explicit offline-only escape hatch — not triggered by default
    if os.getenv("QP_OFFLINE_MODE", "").lower() in {"1", "true", "yes"}:
        logger.warning(
            "QP_OFFLINE_MODE=1 is set — returning SAMPLE data for %s. "
            "This is NOT real market data.",
            symbol,
        )
        return generate_sample_ohlcv(symbol, start, end)

    # ── Primary: yfinance (works reliably on local Windows) ──────────────────
    yf_exc = None
    try:
        df = fetch_from_yfinance(symbol, start, end, exchange)
        if not df.empty:
            logger.info("yfinance success: %d rows for %s (source=%s)", len(df), symbol, df.attrs.get("data_source"))
            return df
        yf_exc = ValueError("yfinance returned empty DataFrame")
    except Exception as exc:
        yf_exc = exc
        logger.warning("yfinance failed for %s: %s — trying nsepy", symbol, exc)

    # ── Fallback: nsepy ───────────────────────────────────────────────────────
    try:
        df = fetch_from_nsepy(symbol, start, end)
        if not df.empty:
            logger.info("nsepy success: %d rows for %s (source=%s)", len(df), symbol, df.attrs.get("data_source"))
            return df
        raise ValueError("nsepy returned empty DataFrame")
    except Exception as nsepy_exc:
        logger.error("nsepy also failed for %s: %s", symbol, nsepy_exc)
        raise RuntimeError(
            f"All real data sources failed for '{symbol}'.\n"
            f"  yfinance: {yf_exc}\n"
            f"  nsepy:    {nsepy_exc}\n"
            f"Check internet connectivity and symbol spelling. "
            f"Set QP_OFFLINE_MODE=1 only if you explicitly want sample data."
        ) from nsepy_exc


def should_use_sample_data() -> bool:
    """
    Returns True ONLY when QP_OFFLINE_MODE=1 is explicitly set.
    QP_USE_LIVE_DATA=1 (or any other env) never triggers sample data.
    """
    return os.getenv("QP_OFFLINE_MODE", "").lower() in {"1", "true", "yes"}


def generate_sample_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Deterministic sample data for QP_OFFLINE_MODE=1 ONLY.
    Always sets df.attrs["data_source"] = "sample" so callers can detect it.
    This function must NOT be called in live/production mode.
    """
    dates = pd.bdate_range(start=start, end=end)
    if dates.empty:
        raise ValueError(f"No business days in range {start} to {end}")

    base = 1800 + (sum(ord(c) for c in symbol.upper()) % 900)
    rows = []
    prev_close = float(base)
    for i, date_idx in enumerate(dates):
        drift = i * 0.55
        cycle = math.sin(i / 8.0) * 55 + math.sin(i / 29.0) * 110
        close = max(10.0, base + drift + cycle)
        open_price = prev_close
        high = max(open_price, close) * 1.012
        low = min(open_price, close) * 0.988
        volume = 1_000_000 + int((math.sin(i / 5.0) + 1) * 250_000)
        rows.append(
            {
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            }
        )
        prev_close = close

    df = pd.DataFrame(rows, index=dates)
    df.index.name = "date"
    df.attrs["data_source"] = "sample"
    return df
