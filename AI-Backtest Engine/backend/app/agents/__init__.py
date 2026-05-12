

import os
import pandas as pd

from .models import BacktestResult
from .strategy_agent import generate_strategy_code          # noqa: F401 — re-exported
from .risk_agent import compute_metrics
from .audit_agent import generate_audit_hash
from ..sandbox.runner import execute_strategy


def run_backtest(
    code: str,
    df: pd.DataFrame,
    initial_capital: float = 100_000.0,
    # Internal context for audit hash — injected by backtest.py task
    symbol: str = "UNKNOWN",
    start: str = "",
    end: str = "",
) -> BacktestResult:
    """
    Execute a vectorbt strategy in the sandbox, compute risk metrics,
    and return a fully-populated BacktestResult dataclass.

    Args:
        code:            Vectorbt Python code string (from generate_strategy_code).
        df:              OHLCV DataFrame with lowercase columns + DatetimeIndex.
        initial_capital: Starting capital in INR.
        symbol:          Ticker symbol — used for audit hash only.
        start:           Start date string — used for audit hash only.
        end:             End date string — used for audit hash only.

    Returns:
        BacktestResult dataclass (serialisable to JSON by Account 1).

    Raises:
        TimeoutError:   If the strategy takes longer than 30 seconds.
        RuntimeError:   If the generated code is invalid or crashes.
    """
    # 1. Run strategy code safely in the sandbox (30 s timeout)
    portfolio = execute_strategy(code, df)

    # 2. Compute all risk / performance metrics
    metrics = compute_metrics(portfolio, df, initial_capital)

    # 3. Generate tamper-proof audit hash
    audit_hash = generate_audit_hash(symbol, start, end, code, metrics)

    # 4. Assemble and return the BacktestResult dataclass
    return BacktestResult(
        total_return_pct=metrics["total_return_pct"],
        cagr=metrics["cagr"],
        sharpe_ratio=metrics["sharpe_ratio"],
        max_drawdown_pct=metrics["max_drawdown_pct"],
        win_rate=metrics["win_rate"],
        total_trades=metrics["total_trades"],
        dsr_score=metrics["dsr_score"],
        equity_curve=metrics["equity_curve"],
        trades=metrics["trades"],
        audit_hash=audit_hash,
    )
