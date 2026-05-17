
import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _fetch_returns(
    symbols: list[str],
    start: str,
    end: str,
    exchange: str = "NSE",
) -> pd.DataFrame:
   
    from .ingest import fetch_ohlcv  # noqa: PLC0415

    close_prices = {}

    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, start, end, exchange)
            if not df.empty and "close" in df.columns:
                close_prices[symbol] = df["close"]
            else:
                logger.warning("No data for %s — skipping from portfolio", symbol)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s — skipping", symbol, exc)

    if not close_prices:
        raise ValueError("No valid symbols fetched. Cannot compute portfolio analytics.")

    prices_df = pd.DataFrame(close_prices).dropna(how="all")
    returns_df = prices_df.pct_change().dropna(how="all")

    logger.info(
        "Portfolio returns: %d symbols, %d rows, %s → %s",
        len(returns_df.columns), len(returns_df), start, end,
    )
    return returns_df


def get_correlation_matrix(
    symbols: list[str],
    start: str,
    end: str,
    exchange: str = "NSE",
) -> dict:
  
    if len(symbols) > 10:
        logger.warning("Portfolio analytics supports max 10 symbols — truncating")
        symbols = symbols[:10]

    returns = _fetch_returns(symbols, start, end, exchange)
    valid_symbols = list(returns.columns)

    corr_matrix = returns.corr(method="pearson")

    # Round to 3 decimal places for JSON serialisation
    matrix_list = corr_matrix.round(3).values.tolist()

    # Flag highly correlated pairs (> 0.8) — risk concentration warning
    high_corr = []
    n = len(valid_symbols)
    for i in range(n):
        for j in range(i + 1, n):
            val = corr_matrix.iloc[i, j]
            if abs(val) > 0.8:
                high_corr.append({
                    "pair": [valid_symbols[i], valid_symbols[j]],
                    "corr": round(float(val), 3),
                })

    high_corr.sort(key=lambda x: abs(x["corr"]), reverse=True)

    return {
        "symbols":           valid_symbols,
        "matrix":            matrix_list,
        "high_correlations": high_corr,
        "warning":           (
            "High correlation detected between some pairs — "
            "diversification benefit may be limited."
        ) if high_corr else None,
    }


def get_portfolio_stats(
    symbols: list[str],
    weights: Optional[list[float]],
    start: str,
    end: str,
    initial_capital: float = 100_000.0,
    exchange: str = "NSE",
) -> dict:
   
    returns = _fetch_returns(symbols, start, end, exchange)
    valid_symbols = list(returns.columns)
    n = len(valid_symbols)

   
    if weights and len(weights) == n:
        w = np.array(weights, dtype=float)
        w = w / w.sum()    
    else:
        w = np.ones(n) / n 

    logger.info(
        "Portfolio stats: %d symbols, weights=%s", n,
        [round(x, 3) for x in w.tolist()]
    )


    portfolio_returns = returns[valid_symbols].values @ w
    portfolio_returns = pd.Series(portfolio_returns, index=returns.index)

    equity = initial_capital * (1 + portfolio_returns).cumprod()

    total_return = (equity.iloc[-1] / initial_capital - 1) * 100
    n_years = len(returns) / 252
    cagr = ((equity.iloc[-1] / initial_capital) ** (1 / max(n_years, 0.01)) - 1) * 100

    sharpe = (
        portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252)
        if portfolio_returns.std() > 0 else 0.0
    )

    drawdown = ((equity / equity.cummax()) - 1).min() * 100

   
    individual = {}
    for sym in valid_symbols:
        sym_prices = returns[sym].add(1).cumprod()
        individual[sym] = round(float((sym_prices.iloc[-1] - 1) * 100), 2)

    equity_curve = [
        {"date": str(d.date()), "value": round(float(v), 2)}
        for d, v in equity.items()
    ]

    return {
        "symbols":              valid_symbols,
        "weights":              w.round(4).tolist(),
        "total_return_pct":     round(float(total_return), 2),
        "cagr":                 round(float(cagr), 2),
        "sharpe_ratio":         round(float(sharpe), 3),
        "max_drawdown_pct":     round(float(drawdown), 2),
        "portfolio_equity_curve": equity_curve,
        "individual_returns":   individual,
    }


def get_drawdown_periods(equity_curve: list[dict]) -> list[dict]:
    
    if not equity_curve:
        return []

    values = pd.Series(
        [e["value"] for e in equity_curve],
        index=pd.to_datetime([e["date"] for e in equity_curve]),
    )

    rolling_max = values.cummax()
    dd = (values / rolling_max) - 1

    periods = []
    in_drawdown = False
    peak_date = None
    trough_date = None
    trough_val = 0.0
    peak_val = 0.0

    for date, val in dd.items():
        if val < 0 and not in_drawdown:
            in_drawdown = True
            peak_date = date
            peak_val = float(rolling_max[date])
            trough_val = float(val)
            trough_date = date

        elif val < trough_val and in_drawdown:
            trough_val = float(val)
            trough_date = date

        elif val >= 0 and in_drawdown:
            in_drawdown = False
            duration = (date - peak_date).days
            if trough_val < -0.05:   # only report drawdowns > 5%
                periods.append({
                    "start":          str(peak_date.date()),
                    "trough":         str(trough_date.date()),
                    "end":            str(date.date()),
                    "drawdown_pct":   round(trough_val * 100, 2),
                    "duration_days":  duration,
                    "peak_value":     round(peak_val, 2),
                })


    if in_drawdown and trough_val < -0.05:
        last_date = dd.index[-1]
        periods.append({
            "start":         str(peak_date.date()),
            "trough":        str(trough_date.date()),
            "end":           None,   # still in drawdown
            "drawdown_pct":  round(trough_val * 100, 2),
            "duration_days": (last_date - peak_date).days,
            "peak_value":    round(peak_val, 2),
        })

    periods.sort(key=lambda x: x["drawdown_pct"])
    return periods
