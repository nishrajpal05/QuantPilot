

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)



def _get_adjustment_factors(symbol: str) -> pd.DataFrame:
  
    try:
        import yfinance as yf  # noqa: PLC0415

        INDEX_MAP = {
            "NIFTY 50": "^NSEI",
            "NIFTY50": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "SENSEX": "^BSESN",
        }
        ticker_str = INDEX_MAP.get(symbol.upper(), symbol + ".NS")
        ticker = yf.Ticker(ticker_str)

        splits = ticker.splits  # pandas Series, index = date, value = ratio
        if splits is None or splits.empty:
            return pd.DataFrame(columns=["date", "factor"])

        splits = splits[splits > 0].sort_index()

        # Build cumulative backward adjustment factors
        # e.g. a 1:2 split means historical prices must be halved
        factors = []
        for date, ratio in splits.items():
            ts = pd.Timestamp(date)
            # yfinance 1.x returns tz-aware split dates — strip timezone
            if ts.tzinfo is not None:
                ts = ts.tz_convert(None)
            factors.append(
                {
                    "date": ts.normalize(),
                    # ratio = new_shares / old_shares, so pre-split price factor = 1/ratio
                    "factor": 1.0 / float(ratio),
                }
            )

        df = pd.DataFrame(factors).sort_values("date").reset_index(drop=True)
        logger.info("Found %d corporate action events for %s", len(df), symbol)
        return df

    except Exception as exc:
        logger.warning(
            "Could not fetch corporate actions for %s: %s — returning unadjusted",
            symbol,
            exc,
        )
        return pd.DataFrame(columns=["date", "factor"])



def adjust_prices(df: pd.DataFrame, symbol: str) -> pd.DataFrame:

    if df is None or df.empty:
        return df

  
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()

    adjustments = _get_adjustment_factors(symbol)
    if adjustments.empty:
        logger.info("No corporate actions found for %s — data unchanged", symbol)
        return df

    for _, row in adjustments.sort_values("date", ascending=False).iterrows():
        event_date: pd.Timestamp = row["date"]
        # Ensure tz-naive for comparison with tz-naive df.index
        if hasattr(event_date, "tzinfo") and event_date.tzinfo is not None:
            event_date = event_date.tz_convert(None)
        factor: float = row["factor"]

        mask = df.index < event_date
        if not mask.any():
            continue

        price_cols = ["open", "high", "low", "close"]
        for col in price_cols:
            if col in df.columns:
                df.loc[mask, col] = df.loc[mask, col] * factor

        if "volume" in df.columns:
            df.loc[mask, "volume"] = df.loc[mask, "volume"] / factor

        logger.info(
            "Applied factor %.4f before %s for %s",
            factor,
            event_date.date(),
            symbol,
        )
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = df[col].round(2)
    if "volume" in df.columns:
        df["volume"] = df["volume"].round(0).astype("int64")

    return df
