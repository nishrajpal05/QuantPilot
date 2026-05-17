import os
import pandas as pd

from .models import BacktestResult
from .strategy_agent import (              # Phase 1 + Phase 2
    generate_strategy_code,
    refine_strategy_code,
    explain_strategy,
)
from .risk_agent import compute_metrics
from .audit_agent import generate_audit_hash
from .alert_agent import dispatch_alert, dispatch_all_alerts    # Phase 2
from .paper_trader import run_paper_trade, run_paper_trade_multi  # Phase 2
from ..sandbox.runner import execute_strategy


def run_backtest(
    code: str,
    df: pd.DataFrame,
    initial_capital: float = 100_000.0,
    symbol: str = "UNKNOWN",
    start: str = "",
    end: str = "",
) -> BacktestResult:
    
    portfolio = execute_strategy(code, df)
    metrics = compute_metrics(portfolio, df, initial_capital)
    audit_hash = generate_audit_hash(symbol, start, end, code, metrics)

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
