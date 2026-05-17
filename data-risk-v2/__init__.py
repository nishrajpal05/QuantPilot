
import logging
from typing import Optional

import pandas as pd

from .corporate_actions import adjust_prices
from .db import (
    clear_fyers_credentials,
    get_fyers_credentials,
    read_cache,
    read_intraday_cache,
    save_fyers_credentials,
    write_cache,
    write_intraday_cache,
)
from .ingest import fetch_bulk_ohlcv, fetch_index_constituents, fetch_ohlcv
from .portfolio import get_correlation_matrix, get_drawdown_periods, get_portfolio_stats
from .websocket_handler import get_live_quote, get_multiple_quotes, start_websocket, stop_websocket

logger = logging.getLogger(__name__)



def _compute_missing_dates(cached: pd.DataFrame, start: str, end: str) -> bool:

    if cached is None or cached.empty:
        return True
    cached_dates = pd.to_datetime(cached.index)
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end)
    has_start = (cached_dates >= start_ts - pd.Timedelta(days=5)).any()
    has_end   = (cached_dates <= end_ts   + pd.Timedelta(days=5)).any()
    return not (has_start and has_end)


def _merge_and_sort(cached: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:

    if cached is None or cached.empty:
        return fresh.sort_index()
    if fresh is None or fresh.empty:
        return cached.sort_index()
    combined = pd.concat([cached, fresh])
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.sort_index()



def get_ohlcv(
    symbol: str,
    start: str,
    end: str,
    exchange: str = "NSE",
) -> pd.DataFrame:
 
    logger.info("get_ohlcv: %s  %s → %s  exchange=%s", symbol, start, end, exchange)

    cached = read_cache(symbol, exchange, start, end)

    if _compute_missing_dates(cached, start, end):
        logger.info("Cache miss — fetching fresh data for %s", symbol)
        fresh_raw      = fetch_ohlcv(symbol, start, end, exchange)
        fresh_adjusted = adjust_prices(fresh_raw, symbol)
        write_cache(symbol, exchange, fresh_adjusted)
        return _merge_and_sort(cached, fresh_adjusted)

    logger.info("Full cache hit for %s", symbol)
    return cached.sort_index()


def get_symbols_list(exchange: str = "NSE") -> list[str]:

    NSE_SYMBOLS = [
        "NIFTY 50", "BANKNIFTY",
        "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
        "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "ICICIGI",
        "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "MPHASIS",
        "COFORGE", "PERSISTENT", "RELIANCE", "ONGC", "IOC", "BPCL",
        "COALINDIA", "NTPC", "POWERGRID", "TATAPOWER", "ADANIPORTS",
        "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO",
        "MARUTI", "TATAMOTORS", "M&M", "HEROMOTOCO", "BAJAJ-AUTO",
        "EICHERMOT", "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB",
        "APOLLOHOSP", "LT", "TATASTEEL", "HINDALCO", "JSWSTEEL",
        "BHARTIARTL", "ULTRACEMCO", "GRASIM", "TITAN", "ASIANPAINT",
        "INDIGO", "ZOMATO", "NYKAA", "PAYTM", "IRCTC",
        "DELHIVERY", "IRFC", "CONCOR", "HAL", "BEL",
    ]
    BSE_SYMBOLS = [
        "SENSEX", "RELIANCE", "TCS", "HDFCBANK", "INFY",
        "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL",
        "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "MARUTI",
        "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS", "WIPRO", "M&M",
    ]
    return BSE_SYMBOLS if exchange.upper() == "BSE" else NSE_SYMBOLS


def get_ohlcv_intraday(
    symbol: str,
    resolution: str,
    start: str,
    end: str,
    user_id: str,
    exchange: str = "NSE",
) -> pd.DataFrame:
    """
    Fetch intraday OHLCV data via Fyers API V3.
    Checks intraday cache before hitting the API.

    Args:
        symbol:     NSE ticker, e.g. 'RELIANCE'
        resolution: '1min', '5min', '15min', '60min'
        start:      'YYYY-MM-DD'
        end:        'YYYY-MM-DD'
        user_id:    UUID of the QuantPilot user (used to look up Fyers token)
        exchange:   'NSE' (default) or 'BSE'

    Returns:
        pd.DataFrame with DatetimeIndex and lowercase columns

    Raises:
        ValueError: if user has not connected Fyers account
    """

    cached = read_intraday_cache(symbol, exchange, resolution, start, end)
    if not _compute_missing_dates(cached, start, end):
        logger.info("Intraday cache hit for %s @%s", symbol, resolution)
        return cached.sort_index()

    creds = get_fyers_credentials(user_id)
    if not creds:
        raise ValueError(
            "Fyers account not connected. "
            "Go to Settings → Connect Fyers to enable intraday backtesting."
        )


    from .fyers_client import FyersClient  # noqa: PLC0415
    client = FyersClient(creds["app_id"], creds["access_token"])
    df = client.get_history(symbol, resolution, start, end, exchange)

    if df is None or df.empty:
        raise RuntimeError(
            f"Fyers returned no intraday data for {symbol} @{resolution} "
            f"({start} → {end}). Check that the symbol and date range are valid."
        )

    write_intraday_cache(symbol, exchange, resolution, df)
    logger.info("Intraday fetch complete: %d rows for %s @%s", len(df), symbol, resolution)
    return df




def get_bulk_ohlcv(
    symbols: list[str],
    start: str,
    end: str,
    exchange: str = "NSE",
) -> dict[str, pd.DataFrame]:

    def _get_one(sym: str):
        return sym, get_ohlcv(sym, start, end, exchange)

    from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: PLC0415

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_get_one, s): s for s in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                sym_out, df = future.result()
                results[sym_out] = df
            except Exception as exc:
                logger.warning("Bulk get_ohlcv failed for %s: %s", sym, exc)

    return results




__all__ = [
    # Phase 1
    "get_ohlcv",
    "get_symbols_list",
    # Phase 2 — data
    "get_ohlcv_intraday",
    "get_bulk_ohlcv",
    "fetch_index_constituents",
    # Phase 2 — portfolio analytics
    "get_correlation_matrix",
    "get_portfolio_stats",
    "get_drawdown_periods",
    # Phase 2 — real-time
    "get_live_quote",
    "get_multiple_quotes",
    "start_websocket",
    "stop_websocket",
    "save_fyers_credentials",
    "get_fyers_credentials",
    "clear_fyers_credentials",
]
