import logging
import time
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

RESOLUTION_MAP = {
    "1min":   "1",
    "2min":   "2",
    "3min":   "3",
    "5min":   "5",
    "10min":  "10",
    "15min":  "15",
    "20min":  "20",
    "30min":  "30",
    "45min":  "45",
    "60min":  "60",
    "120min": "120",
    "D":      "1D",
    "1D":     "1D",
    "day":    "1D",
}

MAX_DAYS_PER_REQUEST = 100

RATE_LIMIT_SLEEP = 0.15


def _to_fyers_symbol(symbol: str, exchange: str = "NSE") -> str:

    INDEX_SYMBOLS = {
        "NIFTY 50":   f"{exchange}:NIFTY50-INDEX",
        "NIFTY50":    f"{exchange}:NIFTY50-INDEX",
        "BANKNIFTY":  f"{exchange}:NIFTYBANK-INDEX",
        "SENSEX":     "BSE:SENSEX-INDEX",
        "NIFTYMIDCAP": f"{exchange}:NIFTYMIDCAP100-INDEX",
    }

    upper = symbol.upper().replace(" ", "")
    if upper in {k.upper().replace(" ", "") for k in INDEX_SYMBOLS}:
        for k, v in INDEX_SYMBOLS.items():
            if k.upper().replace(" ", "") == upper:
                return v

    return f"{exchange}:{symbol}-EQ"


class FyersClient:
    

    def __init__(self, app_id: str, access_token: str):
      
        try:
            from fyers_apiv3 import fyersModel  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "fyers-apiv3 is not installed. Run: pip install fyers-apiv3==3.1.3"
            )

        self.app_id = app_id
        self.fyers = fyersModel.FyersModel(
            client_id=app_id,
            token=access_token,
            is_async=False,
            log_path="",        # suppress Fyers SDK file logging
        )
        logger.info("FyersClient initialised for app_id=%s", app_id)

    def get_history(
        self,
        symbol: str,
        resolution: str,
        start: str,
        end: str,
        exchange: str = "NSE",
    ) -> pd.DataFrame:
        
        res_code = RESOLUTION_MAP.get(resolution)
        if res_code is None:
            raise ValueError(
                f"Unsupported resolution '{resolution}'. "
                f"Valid options: {list(RESOLUTION_MAP.keys())}"
            )

        fyers_symbol = _to_fyers_symbol(symbol, exchange)
        logger.info(
            "Fyers fetch: %s (%s) resolution=%s  %s → %s",
            symbol, fyers_symbol, resolution, start, end,
        )

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt   = datetime.strptime(end,   "%Y-%m-%d")

        all_candles = []
        chunk_end   = end_dt
        page        = 0

        while chunk_end > start_dt:
            chunk_start = max(start_dt, chunk_end - timedelta(days=MAX_DAYS_PER_REQUEST))
            page += 1

            logger.debug(
                "Fyers page %d: %s → %s",
                page,
                chunk_start.strftime("%Y-%m-%d"),
                chunk_end.strftime("%Y-%m-%d"),
            )

            resp = self.fyers.history({
                "symbol":      fyers_symbol,
                "resolution":  res_code,
                "date_format": "1",                         
                "range_from":  chunk_start.strftime("%Y-%m-%d"),
                "range_to":    chunk_end.strftime("%Y-%m-%d"),
                "cont_flag":   "1",                        
            })

            if resp.get("s") != "ok":
                error_msg = resp.get("message", str(resp))
          
                if "token" in error_msg.lower() or "auth" in error_msg.lower():
                    raise RuntimeError(
                        "Fyers access token is expired or invalid. "
                        "Please reconnect your Fyers account in Settings."
                    )
                raise RuntimeError(f"Fyers API error for {symbol}: {error_msg}")

            candles = resp.get("candles", [])
            all_candles.extend(candles)
            logger.debug("Page %d returned %d candles", page, len(candles))

            chunk_end = chunk_start - timedelta(days=1)

            
            if chunk_end > start_dt:
                time.sleep(RATE_LIMIT_SLEEP)

        if not all_candles:
            logger.warning("Fyers returned 0 candles for %s", symbol)
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(
            all_candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(
            "Asia/Kolkata"
        ).dt.tz_localize(None)

        df = df.set_index("date").sort_index()
        df = df[["open", "high", "low", "close", "volume"]]

       
        df = df[~df.index.duplicated(keep="last")]

        logger.info(
            "Fyers fetch complete: %d rows for %s (%d pages)", len(df), symbol, page
        )
        return df

    def get_quotes(self, symbols: list[str], exchange: str = "NSE") -> dict:
        
        fyers_symbols = [_to_fyers_symbol(s, exchange) for s in symbols]
        resp = self.fyers.quotes({"symbols": ",".join(fyers_symbols)})

        if resp.get("s") != "ok":
            raise RuntimeError(f"Fyers quotes error: {resp.get('message', resp)}")

        result = {}
        for item in resp.get("d", []):
            v = item.get("v", {})
            original_symbol = item["n"].split(":")[1].replace("-EQ", "").replace("-INDEX", "")
            result[original_symbol] = {
                "ltp":    v.get("lp"),
                "open":   v.get("open_price"),
                "high":   v.get("high_price"),
                "low":    v.get("low_price"),
                "volume": v.get("volume"),
                "change_pct": v.get("ch"),
            }
        return result
