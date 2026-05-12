from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/data", tags=["data"])

# Fallback symbol list used before Account 2 is merged
_FALLBACK_NSE_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "ITC", "WIPRO",
    "AXISBANK", "LT", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN",
    "ULTRACEMCO", "NESTLEIND", "POWERGRID", "NTPC", "ONGC", "COALINDIA",
    "JSWSTEEL", "TATAMOTORS", "TATASTEEL", "HCLTECH", "TECHM", "M&M",
    "ADANIENT", "ADANIPORTS", "BAJAJFINSV", "BAJAJ-AUTO", "BRITANNIA",
    "CIPLA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HEROMOTOCO",
    "HINDALCO", "INDUSINDBK", "SBILIFE", "HDFCLIFE", "APOLLOHOSP",
    "BPCL", "TATACONSUM", "UPL", "VEDL",
]

_FALLBACK_BSE_SYMBOLS = [
    "500325", "532540", "500209", "500180", "532174", "500696",
    "500112", "500034", "532454", "500247",
]


@router.get("/symbols")
def get_symbols(
    exchange: str = Query(default="NSE", pattern="^(NSE|BSE)$"),
    _: dict = Depends(get_current_user),
):
    """
    Returns list of valid ticker symbols.
    Uses Account 2's get_symbols_list() after merge; falls back to hardcoded list.
    """
    try:
        from app.data import get_symbols_list
        return {"exchange": exchange, "symbols": get_symbols_list(exchange)}
    except ImportError:
        symbols = _FALLBACK_NSE_SYMBOLS if exchange == "NSE" else _FALLBACK_BSE_SYMBOLS
        return {"exchange": exchange, "symbols": symbols, "source": "fallback"}


@router.get("/ohlcv/{symbol}")
def get_ohlcv_preview(
    symbol: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str   = Query(..., description="YYYY-MM-DD"),
    exchange: str = Query(default="NSE", pattern="^(NSE|BSE)$"),
    _: dict = Depends(get_current_user),
):
    """
    Returns OHLCV preview (last 10 rows) for a symbol.
    Used by frontend to validate symbol before running a backtest.
    """
    try:
        from app.data import get_ohlcv
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Data module not yet available. Merge Account 2 branch first."
        )

    try:
        df = get_ohlcv(symbol.upper(), start, end, exchange)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch data: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

    # Return last 10 rows as preview
    preview = df.tail(10).reset_index()
    return {
        "symbol":    symbol.upper(),
        "exchange":  exchange,
        "rows_total": len(df),
        "preview":   preview.to_dict("records"),
    }
