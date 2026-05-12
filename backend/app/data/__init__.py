
import logging
from typing import Optional

import pandas as pd

from .corporate_actions import adjust_prices
from .db import read_cache, write_cache
from .ingest import fetch_ohlcv

logger = logging.getLogger(__name__)


def _compute_missing_dates(
    cached: pd.DataFrame,
    start: str,
    end: str,
) -> bool:
    if cached is None or cached.empty:
        return True

    cached_dates = pd.to_datetime(cached.index)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    # Allow a 5-day slack for weekends / market holidays at boundaries
    has_start = (cached_dates >= start_ts - pd.Timedelta(days=5)).any()
    has_end = (cached_dates >= end_ts - pd.Timedelta(days=5)).any()

    return not (has_start and has_end)


def _merge_and_sort(
    cached: pd.DataFrame,
    fresh: pd.DataFrame,
) -> pd.DataFrame:

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
    """
    Fetch real OHLCV data for the given symbol/range.

    Flow:
      1. Try the Supabase cache (read_cache).
      2. If cache miss/incomplete → fetch fresh via fetch_ohlcv() (yfinance → nsepy).
      3. Write fresh data back to cache.
      4. Return merged/sorted DataFrame.

    The returned DataFrame always carries:
      df.attrs["data_source"] = "yfinance" | "nsepy" | "cache" | "sample"
      df.attrs["rows_used"]   = int (number of rows in the final slice)

    Raises RuntimeError (propagated from ingest.py) if real data cannot be fetched
    and QP_OFFLINE_MODE is not set.
    """
    logger.info("get_ohlcv called: symbol=%s  %s → %s  exchange=%s", symbol, start, end, exchange)

    cached = read_cache(symbol, exchange, start, end)

    if _compute_missing_dates(cached, start, end):
        logger.info("Cache miss or incomplete — fetching fresh data for %s", symbol)

        # fetch_ohlcv raises RuntimeError if both providers fail (no silent fallback)
        fresh_raw = fetch_ohlcv(symbol, start, end, exchange)
        data_source = fresh_raw.attrs.get("data_source", "unknown")

        fresh_adjusted = adjust_prices(fresh_raw, symbol)
        # Preserve the data_source attr through adjust_prices
        fresh_adjusted.attrs["data_source"] = data_source

        write_cache(symbol, exchange, fresh_adjusted)

        merged = _merge_and_sort(cached, fresh_adjusted)
        merged.attrs["data_source"] = data_source
        merged.attrs["rows_used"] = len(merged)
        return merged

    logger.info("Full cache hit for %s — skipping network fetch", symbol)
    cached.attrs["data_source"] = "cache"
    cached.attrs["rows_used"] = len(cached)
    return cached.sort_index()


def get_symbols_list(exchange: str = "NSE") -> list[str]:

    # Top NSE F&O + large-cap symbols covering ~80% of retail backtest demand
    NSE_SYMBOLS = [
        # Index
        "NIFTY 50",
        "BANKNIFTY",
        # Large Cap — Banking & Finance
        "HDFCBANK",
        "ICICIBANK",
        "KOTAKBANK",
        "AXISBANK",
        "SBIN",
        "BAJFINANCE",
        "BAJAJFINSV",
        "HDFCLIFE",
        "SBILIFE",
        "ICICIGI",
        # Large Cap — IT
        "TCS",
        "INFY",
        "WIPRO",
        "HCLTECH",
        "TECHM",
        "LTIM",
        "MPHASIS",
        "COFORGE",
        "PERSISTENT",
        # Large Cap — Energy & Commodities
        "RELIANCE",
        "ONGC",
        "IOC",
        "BPCL",
        "COALINDIA",
        "NTPC",
        "POWERGRID",
        "TATAPOWER",
        "ADANIPORTS",
        "ADANIENT",
        # Large Cap — FMCG & Consumer
        "HINDUNILVR",
        "ITC",
        "NESTLEIND",
        "BRITANNIA",
        "DABUR",
        "MARICO",
        "GODREJCP",
        "TATACONSUM",
        "COLPAL",
        # Large Cap — Auto
        "MARUTI",
        "TATAMOTORS",
        "M&M",
        "HEROMOTOCO",
        "BAJAJ-AUTO",
        "EICHERMOT",
        "ASHOKLEY",
        "TVSMOTOR",
        # Large Cap — Pharma & Healthcare
        "SUNPHARMA",
        "DRREDDY",
        "CIPLA",
        "DIVISLAB",
        "APOLLOHOSP",
        "AUROPHARMA",
        "TORNTPHARM",
        "BIOCON",
        # Large Cap — Infra & Industrials
        "LT",
        "SIEMENS",
        "ABB",
        "HAVELLS",
        "POLYCAB",
        "BHEL",
        "BEL",
        "HAL",
        "IRFC",
        # Large Cap — Metals & Mining
        "TATASTEEL",
        "HINDALCO",
        "JSWSTEEL",
        "SAIL",
        "VEDL",
        "NATIONALUM",
        # Large Cap — Telecom & Media
        "BHARTIARTL",
        "IDEA",
        "ZEEL",
        "PVR",
        # Large Cap — Cement & Building
        "ULTRACEMCO",
        "SHREECEM",
        "GRASIM",
        "AMBUJACEMENT",
        "ACC",
        # Mid Cap — select high-activity F&O names
        "INDIGO",
        "DIXON",
        "ZOMATO",
        "NYKAA",
        "PAYTM",
        "DELHIVERY",
        "IRCTC",
        "CONCOR",
        "CANBK",
        "PNB",
        "BANKBARODA",
        "FEDERALBNK",
        "IDFCFIRSTB",
        "RBLBANK",
        "METROPOLIS",
        "LALPATHLAB",
        "CHOLAFIN",
        "MUTHOOTFIN",
        "MANAPPURAM",
        "SRF",
        "PIIND",
        "AARTIIND",
    ]

    BSE_SYMBOLS = [
        "SENSEX",
        "RELIANCE",
        "TCS",
        "HDFCBANK",
        "INFY",
        "ICICIBANK",
        "HINDUNILVR",
        "ITC",
        "SBIN",
        "BHARTIARTL",
        "KOTAKBANK",
        "LT",
        "AXISBANK",
        "BAJFINANCE",
        "MARUTI",
        "SUNPHARMA",
        "ULTRACEMCO",
        "TATAMOTORS",
        "WIPRO",
        "M&M",
        "NTPC",
        "POWERGRID",
        "ONGC",
        "DRREDDY",
        "CIPLA",
        "TATASTEEL",
        "HINDALCO",
        "JSWSTEEL",
        "GRASIM",
        "BAJAJ-AUTO",
    ]

    if exchange.upper() == "BSE":
        return BSE_SYMBOLS

    return NSE_SYMBOLS
