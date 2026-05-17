
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)



def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:

    df.columns = [c.lower() for c in df.columns]
    ohlcv = ["open", "high", "low", "close", "volume"]
    available = [c for c in ohlcv if c in df.columns]
    return df[available].copy()



def fetch_from_nsepy(symbol: str, start: str, end: str) -> pd.DataFrame:
  
    try:
        import nsepy  # noqa: PLC0415
    except ImportError:
        raise ImportError("nsepy not installed. Run: pip install nsepy")

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt   = datetime.strptime(end,   "%Y-%m-%d")

    logger.info("nsepy fetch: %s  %s → %s", symbol, start, end)
    raw = nsepy.get_history(symbol=symbol, start=start_dt, end=end_dt)

    if raw is None or raw.empty:
        raise ValueError(f"nsepy returned empty DataFrame for {symbol}")

    df = _normalise_columns(raw[["Open", "High", "Low", "Close", "Volume"]])
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df


def fetch_from_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:

    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        raise ImportError("yfinance not installed. Run: pip install yfinance")

    INDEX_MAP = {
        "NIFTY 50":  "^NSEI",
        "NIFTY50":   "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX":    "^BSESN",
    }
    ticker_str = INDEX_MAP.get(symbol.upper(), symbol + ".NS")

    logger.info("yfinance fetch: %s (%s)  %s → %s", symbol, ticker_str, start, end)
    raw = yf.download(ticker_str, start=start, end=end, progress=False, auto_adjust=True)

    if raw is None or raw.empty:
        raise ValueError(f"yfinance returned empty DataFrame for {ticker_str}")

    df = _normalise_columns(raw[["Open", "High", "Low", "Close", "Volume"]])
    df.index = pd.to_datetime(df.index).tz_localize(None)
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
        logger.warning("nsepy failed for %s (%s) — falling back to yfinance", symbol, primary_exc)
        try:
            df = fetch_from_yfinance(symbol, start, end)
            logger.info("yfinance success: %d rows for %s", len(df), symbol)
            return df
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Both data sources failed for {symbol}. "
                f"nsepy: {primary_exc} | yfinance: {fallback_exc}"
            ) from fallback_exc



def fetch_bulk_ohlcv(
    symbols: list[str],
    start: str,
    end: str,
    exchange: str = "NSE",
    max_workers: int = 5,
) -> dict[str, pd.DataFrame]:
    
    results: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}

    logger.info("Bulk fetch: %d symbols, %s → %s", len(symbols), start, end)

    def _fetch_one(sym: str):
        return sym, fetch_ohlcv(sym, start, end, exchange)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, sym): sym for sym in symbols}

        for future in as_completed(futures):
            sym = futures[future]
            try:
                sym_out, df = future.result()
                results[sym_out] = df
                logger.info("Bulk: fetched %s (%d rows)", sym, len(df))
            except Exception as exc:
                errors[sym] = str(exc)
                logger.warning("Bulk: failed %s — %s", sym, exc)

    if errors:
        logger.warning("Bulk fetch completed with %d errors: %s", len(errors), errors)

    logger.info(
        "Bulk fetch complete: %d/%d symbols successful",
        len(results), len(symbols),
    )
    return results




NIFTY50_CONSTITUENTS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL",
    "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC",
    "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA",
    "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM",
    "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "ZOMATO",
]

NIFTY500_SAMPLE = NIFTY50_CONSTITUENTS + [
    "ABBOTT", "ACC", "AFFLE", "AARTIIND", "ADANIGREEN",
    "ADANITRANS", "ALKEM", "AMBUJACEM", "APLAPOLLO", "APLLTD",
    "ASHOKLEY", "ASTRAL", "AUROPHARMA", "BANKBARODA", "BEL",
    "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK",
    "CHOLAFIN", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL",
    "CROMPTON", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR",
    "DELTACORP", "DELHIVERY", "DIXON", "DLF", "ESCORTS",
    "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA",
    "GODREJCP", "GODREJPROP", "GRANULES", "GSPL", "GUJGASLTD",
    "HAL", "HAVELLS", "HPCL", "IDFCFIRSTB", "IGL",
    "INDHOTEL", "INDIGO", "IRCTC", "IRFC", "JINDALSTEL",
    "JUBLFOOD", "KAJARIACER", "KALPATPOWR", "KANSAINER", "LAURUSLABS",
    "LALPATHLAB", "LICHSGFIN", "LTIM", "LTTS", "LUPIN",
    "MANAPPURAM", "MARICO", "METROPOLIS", "MINDTREE", "MPHASIS",
    "MRF", "MUTHOOTFIN", "NATIONALUM", "NAVINFLUOR", "NAUKRI",
    "NESTLEIND", "NYKAA", "OBEROIRLTY", "OFSS", "PAGEIND",
    "PAYTM", "PERSISTENT", "PETRONET", "PFC", "PIIND",
    "POLYCAB", "PNB", "PVRINOX", "RBLBANK", "RECLTD",
    "SAIL", "SHREECEM", "SRF", "STARHEALTH", "SUMICHEM",
    "SUPREMEIND", "SYNGENE", "TORNTPHARM", "TORNTPOWER", "TRENT",
    "TVSMOTOR", "UBL", "VEDL", "VOLTAS", "ZEEL",
]


def fetch_index_constituents(
    index: str = "NIFTY50",
    exchange: str = "NSE",
) -> list[str]:
    
    BANKNIFTY_CONSTITUENTS = [
        "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
        "BANKBARODA", "IDFCFIRSTB", "INDUSINDBK", "FEDERALBNK", "BANDHANBNK",
        "AUBANK", "PNB",
    ]

    index_map = {
        "NIFTY50":   NIFTY50_CONSTITUENTS,
        "NIFTY 50":  NIFTY50_CONSTITUENTS,
        "NIFTY500":  NIFTY500_SAMPLE,
        "NIFTY 500": NIFTY500_SAMPLE,
        "BANKNIFTY": BANKNIFTY_CONSTITUENTS,
    }

    constituents = index_map.get(index.upper().replace(" ", "").replace("NIFTY", "NIFTY"))
    if constituents is None:

        logger.warning("Unknown index '%s' — defaulting to NIFTY50", index)
        constituents = NIFTY50_CONSTITUENTS

    logger.info("Index constituents: %s → %d symbols", index, len(constituents))
    return list(constituents)
