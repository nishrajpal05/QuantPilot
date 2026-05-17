
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from app.sandbox.runner import execute_strategy

logger = logging.getLogger(__name__)


def _date_range_last_n_days(n: int = 30) -> tuple[str, str]:
    """Return (start, end) date strings for the last N calendar days."""
    end = date.today()
    start = end - timedelta(days=n)
    return start.isoformat(), end.isoformat()


def _determine_signal(portfolio) -> str:
    """
    Infer the current position signal from the portfolio's last position state.

    vectorbt represents position state in the trades records.  We look at
    whether the portfolio currently holds a position (last trade is open)
    to determine if we are in a 'buy' (long) or 'sell'/'hold' state.
    """
    try:
        # Active positions: trades that are currently open
        open_positions = portfolio.positions.records_readable
        if len(open_positions) > 0:
            # Has an open long position → current signal is 'buy' (hold existing)
            last_direction = open_positions.iloc[-1].get("Direction", "Long")
            if "Short" in str(last_direction):
                return "sell"
            return "buy"
        else:
            return "hold"
    except Exception:
        # Fallback: look at the last entry signal value
        try:
            entries = portfolio.entry_signals
            if entries is not None and len(entries) > 0:
                return "buy" if bool(entries.iloc[-1]) else "hold"
        except Exception:
            pass
        return "hold"


def _extract_recent_trades(portfolio, max_trades: int = 10) -> list[dict]:
    """Extract the most recent completed trades as a list of dicts."""
    try:
        trades = portfolio.trades.records_readable
        if trades.empty:
            return []
        recent = trades.tail(max_trades)
        return (
            recent[["Entry Index", "Exit Index", "PnL", "Return"]]
            .rename(columns={
                "Entry Index": "entry_date",
                "Exit Index": "exit_date",
                "PnL": "pnl",
                "Return": "return_pct",
            })
            .assign(
                entry_date=lambda x: x["entry_date"].astype(str),
                exit_date=lambda x: x["exit_date"].astype(str),
                pnl=lambda x: x["pnl"].round(2),
                return_pct=lambda x: (x["return_pct"] * 100).round(3),
            )
            .to_dict("records")
        )
    except Exception as exc:
        logger.warning("[paper_trader] Could not extract trades: %s", exc)
        return []



def run_paper_trade(
    code: str,
    symbol: str,
    initial_capital: float = 100_000.0,
    lookback_days: int = 90,
) -> dict:
    """
    Run a strategy on recent live data to produce the current trading signal.

    Uses 90 days of history (not just 30) so indicators like RSI, MACD, and
    moving averages have enough warmup data.  Only the last 30 days of
    results are surfaced in the response.

    Args:
        code:             Vectorbt Python code string (from strategy_agent).
        symbol:           NSE ticker e.g. 'RELIANCE'.
        initial_capital:  Starting capital in INR (default 1 lakh).
        lookback_days:    Days of historical data to fetch (default 90 for warmup).

    Returns:
        dict with:
          current_signal    'buy' | 'sell' | 'hold'
          current_price     Latest close price (INR)
          simulated_pnl     Paper P&L in INR over the window
          simulated_return  Return % over the window
          recent_trades     List of trade dicts (last 10)
          data_start        Actual data start date
          data_end          Actual data end date
          symbol            Echo of symbol
          error             None or error message string
    """
    # Fetch recent data via Account 2's pipeline
    try:
        from app.data import get_ohlcv
        start, end = _date_range_last_n_days(lookback_days)
        logger.info("[paper_trader] Fetching %s from %s to %s", symbol, start, end)
        df = get_ohlcv(symbol=symbol, start=start, end=end)

        if df is None or df.empty:
            raise ValueError(f"No recent data available for {symbol}")

        logger.info("[paper_trader] Got %d rows of live data", len(df))

    except Exception as exc:
        logger.error("[paper_trader] Data fetch failed: %s", exc)
        return {
            "current_signal": "hold",
            "current_price": None,
            "simulated_pnl": None,
            "simulated_return": None,
            "recent_trades": [],
            "data_start": None,
            "data_end": None,
            "symbol": symbol,
            "error": f"Data fetch failed: {exc}",
        }

    try:
        logger.info("[paper_trader] Executing strategy in sandbox")
        portfolio = execute_strategy(code, df)

    except TimeoutError:
        return {
            "current_signal": "hold",
            "current_price": float(df["close"].iloc[-1]) if not df.empty else None,
            "simulated_pnl": None,
            "simulated_return": None,
            "recent_trades": [],
            "data_start": str(df.index[0].date()) if not df.empty else None,
            "data_end": str(df.index[-1].date()) if not df.empty else None,
            "symbol": symbol,
            "error": "Strategy timed out after 30 seconds",
        }

    except Exception as exc:
        logger.error("[paper_trader] Strategy execution failed: %s", exc)
        return {
            "current_signal": "hold",
            "current_price": float(df["close"].iloc[-1]) if not df.empty else None,
            "simulated_pnl": None,
            "simulated_return": None,
            "recent_trades": [],
            "data_start": str(df.index[0].date()) if not df.empty else None,
            "data_end": str(df.index[-1].date()) if not df.empty else None,
            "symbol": symbol,
            "error": f"Strategy execution failed: {exc}",
        }

    try:
        current_price = float(df["close"].iloc[-1])
        equity = portfolio.value()
        final_value = float(equity.iloc[-1])
        simulated_pnl = round(final_value - initial_capital, 2)
        simulated_return = round((final_value / initial_capital - 1) * 100, 3)

        current_signal = _determine_signal(portfolio)
        recent_trades = _extract_recent_trades(portfolio, max_trades=10)

        logger.info(
            "[paper_trader] Done — signal=%s price=%.2f pnl=%.2f return=%.2f%%",
            current_signal, current_price, simulated_pnl, simulated_return,
        )

        return {
            "current_signal": current_signal,
            "current_price": current_price,
            "simulated_pnl": simulated_pnl,
            "simulated_return": simulated_return,
            "recent_trades": recent_trades,
            "data_start": str(df.index[0].date()),
            "data_end": str(df.index[-1].date()),
            "symbol": symbol,
            "error": None,
        }

    except Exception as exc:
        logger.error("[paper_trader] Result extraction failed: %s", exc)
        return {
            "current_signal": "hold",
            "current_price": float(df["close"].iloc[-1]) if not df.empty else None,
            "simulated_pnl": None,
            "simulated_return": None,
            "recent_trades": [],
            "data_start": str(df.index[0].date()) if not df.empty else None,
            "data_end": str(df.index[-1].date()) if not df.empty else None,
            "symbol": symbol,
            "error": f"Result extraction failed: {exc}",
        }


def run_paper_trade_multi(
    code: str,
    symbols: list[str],
    initial_capital: float = 100_000.0,
    lookback_days: int = 90,
) -> list[dict]:
    """
    Run paper trading simulation across multiple symbols.

    Useful for portfolio-level signal scanning — show users which of their
    watchlist symbols are currently generating a buy/sell from their strategy.

    Args:
        code:             Vectorbt Python code string.
        symbols:          List of NSE tickers (e.g. ['RELIANCE', 'TCS', 'INFY']).
        initial_capital:  Per-symbol starting capital.
        lookback_days:    Days of historical data to fetch per symbol.

    Returns:
        List of paper trade result dicts (one per symbol), sorted by signal
        priority: buy > sell > hold, then by simulated_return desc.
    """
    logger.info("[paper_trader] Multi-symbol scan: %s", symbols)
    results = []

    for symbol in symbols:
        result = run_paper_trade(
            code=code,
            symbol=symbol,
            initial_capital=initial_capital,
            lookback_days=lookback_days,
        )
        results.append(result)

    # Sort: buy first, then sell, then hold; within each group sort by return
    signal_order = {"buy": 0, "sell": 1, "hold": 2}
    results.sort(
        key=lambda r: (
            signal_order.get(r["current_signal"], 99),
            -(r["simulated_return"] or 0),
        )
    )

    buy_count  = sum(1 for r in results if r["current_signal"] == "buy")
    sell_count = sum(1 for r in results if r["current_signal"] == "sell")
    hold_count = sum(1 for r in results if r["current_signal"] == "hold")
    logger.info(
        "[paper_trader] Multi scan complete — buy=%d sell=%d hold=%d",
        buy_count, sell_count, hold_count,
    )

    return results
