import math
import numpy as np
import pandas as pd


def compute_metrics(portfolio, df: pd.DataFrame, initial_capital: float) -> dict:
    """
    Compute comprehensive risk and performance metrics from a vectorbt portfolio.

    Args:
        portfolio:       vectorbt Portfolio object returned by sandbox runner.
        df:              Original OHLCV DataFrame used for the backtest.
        initial_capital: Starting capital in INR (e.g. 100000.0).

    Returns:
        Dictionary containing all metrics needed to build BacktestResult.
    """
    returns = portfolio.returns()
    equity = portfolio.value()

    # ── Core performance metrics ──────────────────────────────────────────────
    total_return = (equity.iloc[-1] / initial_capital - 1) * 100

    n_years = len(df) / 252
    cagr = ((equity.iloc[-1] / initial_capital) ** (1 / n_years) - 1) * 100

    returns_std = returns.std()
    sharpe = 0.0 if returns_std == 0 or np.isnan(returns_std) else returns.mean() / returns_std * np.sqrt(252)

    drawdown = ((equity / equity.cummax()) - 1).min() * 100

    # ── Trade statistics ──────────────────────────────────────────────────────
    trades = portfolio.trades.records_readable
    win_rate = (trades["PnL"] > 0).mean() if len(trades) else 0.0

    # ── Deflated Sharpe Ratio ─────────────────────────────────────────────────
    dsr = compute_dsr(float(sharpe), len(trades), returns)

    # ── Equity curve (serialisable list of dicts) ─────────────────────────────
    equity_curve = [
        {"date": str(d)[:10], "value": round(float(v), 2)}
        for d, v in equity.items()
    ]

    # ── Trade list (serialisable) ─────────────────────────────────────────────
    entry_col = "Entry Timestamp" if "Entry Timestamp" in trades.columns else "Entry Index"
    exit_col = "Exit Timestamp" if "Exit Timestamp" in trades.columns else "Exit Index"
    trade_cols = [entry_col, exit_col, "PnL"]
    if "Return" in trades.columns:
        trade_cols.append("Return")

    trades_list = trades[trade_cols].rename(
        columns={
            entry_col: "entry_date",
            exit_col: "exit_date",
            "PnL": "pnl",
            "Return": "return_pct",
        }
    )
    trades_list["entry_date"] = trades_list["entry_date"].astype(str)
    trades_list["exit_date"] = trades_list["exit_date"].astype(str)
    trades_list["pnl"] = trades_list["pnl"].round(2)
    if "return_pct" in trades_list.columns:
        trades_list["return_pct"] = (trades_list["return_pct"] * 100).round(2)
    trades_list = trades_list.to_dict("records")

    return {
        "total_return_pct": round(float(total_return), 2),
        "cagr": round(float(cagr), 2),
        "sharpe_ratio": round(float(sharpe), 3),
        "max_drawdown_pct": round(float(drawdown), 2),
        "win_rate": round(float(win_rate), 3),
        "total_trades": int(len(trades)),
        "dsr_score": round(float(dsr), 3),
        "equity_curve": equity_curve,
        "trades": trades_list,
    }


def compute_dsr(sharpe: float, n_trades: int, returns: pd.Series) -> float:
    """
    Deflated Sharpe Ratio — penalises overfitting due to multiple trials.

    A DSR > 0.5 indicates the strategy's Sharpe is unlikely to be a
    statistical artefact.  Returns 0.0 if there are fewer than 5 trades
    (insufficient data).

    Reference: Bailey & López de Prado (2014).
    """
    if n_trades < 5:
        return 0.0

    skew = float(returns.skew())
    kurt = float(returns.kurtosis())
    n = len(returns)
    if n == 0 or not np.isfinite(sharpe):
        return 0.0

    # Adjust Sharpe for non-normality of returns
    sr_adj = sharpe * (
        1 - skew * (sharpe / n ** 0.5) + ((kurt - 1) / 4) * (sharpe ** 2 / n)
    ) ** 0.5

    if not np.isfinite(sr_adj):
        return 0.0

    return float(0.5 * (1.0 + math.erf(sr_adj / math.sqrt(2.0))))
