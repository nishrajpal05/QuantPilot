import logging

import numpy as np
import pandas as pd

from .models import MonteCarloResult, WalkForwardResult, WalkForwardWindow

logger = logging.getLogger(__name__)



def compute_metrics(
    portfolio,
    df: pd.DataFrame,
    initial_capital: float,
) -> dict:
   
    returns = portfolio.returns()
    equity  = portfolio.value()

    total_return = (equity.iloc[-1] / initial_capital - 1) * 100
    n_years = max(len(df) / 252, 0.01)
    cagr = ((equity.iloc[-1] / initial_capital) ** (1 / n_years) - 1) * 100

    sharpe = (
        returns.mean() / returns.std() * np.sqrt(252)
        if returns.std() > 0 else 0.0
    )
    drawdown = ((equity / equity.cummax()) - 1).min() * 100

    trades = portfolio.trades.records_readable
    win_rate = float((trades["PnL"] > 0).mean()) if len(trades) > 0 else 0.0

    dsr = compute_dsr(float(sharpe), len(trades), returns)

    equity_curve = [
        {"date": str(d.date()) if hasattr(d, "date") else str(d), "value": round(float(v), 2)}
        for d, v in equity.items()
    ]

    trades_list = (
        trades[["Entry Index", "Exit Index", "PnL"]]
        .rename(columns={"Entry Index": "entry_date", "Exit Index": "exit_date", "PnL": "pnl"})
        .to_dict("records")
    ) if len(trades) > 0 else []

    return {
        "total_return_pct": round(float(total_return), 2),
        "cagr":             round(float(cagr), 2),
        "sharpe_ratio":     round(float(sharpe), 3),
        "max_drawdown_pct": round(float(drawdown), 2),
        "win_rate":         round(float(win_rate), 3),
        "total_trades":     int(len(trades)),
        "dsr_score":        round(float(dsr), 3),
        "equity_curve":     equity_curve,
        "trades":           trades_list,
    }


def compute_dsr(sharpe: float, n_trades: int, returns: pd.Series) -> float:
  
    if n_trades < 5:
        return 0.0

    skew = float(returns.skew())
    kurt = float(returns.kurtosis())
    n    = len(returns)

    if n < 10 or sharpe == 0:
        return 0.0

    try:
        sr_adj = sharpe * (
            1 - skew * (sharpe / n ** 0.5)
            + ((kurt - 1) / 4) * (sharpe ** 2 / n)
        ) ** 0.5
    except (ValueError, ZeroDivisionError):
        return 0.0

    from scipy.stats import norm  # noqa: PLC0415
    return float(norm.cdf(sr_adj))



def run_monte_carlo(
    equity_curve: list[dict],
    n_simulations: int = 1000,
    n_days: int = 252,
) -> dict:
    if not equity_curve or len(equity_curve) < 10:
        logger.warning("Equity curve too short for Monte Carlo — need ≥10 points")
        return MonteCarloResult(
            median_return=1.0, percentile_5=1.0, percentile_95=1.0,
            prob_profit=0.5, simulations=[], n_simulations=0, n_days=n_days,
        ).to_dict()

    values = pd.Series([e["value"] for e in equity_curve], dtype=float)
    daily_returns = values.pct_change().dropna()

    mu  = float(daily_returns.mean())
    std = float(daily_returns.std())

    if std == 0:
        logger.warning("Zero std in equity curve — Monte Carlo not meaningful")
        return MonteCarloResult(
            median_return=1.0, percentile_5=1.0, percentile_95=1.0,
            prob_profit=0.5, simulations=[], n_simulations=n_simulations, n_days=n_days,
        ).to_dict()

    logger.info(
        "Monte Carlo: %d simulations × %d days  mu=%.4f std=%.4f",
        n_simulations, n_days, mu, std,
    )

    np.random.seed(42)  
    terminal_values = []
    sample_paths    = []  

    for i in range(n_simulations):
        daily = np.random.normal(mu, std, n_days)
        path  = np.cumprod(1 + daily)          # cumulative return path
        terminal_values.append(float(path[-1]))
        if i < 100:
            sample_paths.append(path.tolist())

    terminal = np.array(terminal_values)

    result = MonteCarloResult(
        median_return  = float(np.median(terminal)),
        percentile_5   = float(np.percentile(terminal, 5)),
        percentile_95  = float(np.percentile(terminal, 95)),
        prob_profit    = float((terminal > 1.0).mean()),
        simulations    = sample_paths,
        n_simulations  = n_simulations,
        n_days         = n_days,
    )

    logger.info(
        "Monte Carlo complete: median=%.3f  P5=%.3f  P95=%.3f  prob_profit=%.2f",
        result.median_return, result.percentile_5,
        result.percentile_95, result.prob_profit,
    )
    return result.to_dict()




def execute_and_get_sharpe(code: str, df: pd.DataFrame) -> float:
    
    if df is None or len(df) < 20:
        return 0.0

    try:
    
        from app.sandbox.runner import execute_strategy  

        portfolio = execute_strategy(code, df)
        returns   = portfolio.returns()

        if returns.std() == 0 or len(returns) < 5:
            return 0.0

        sharpe = float(returns.mean() / returns.std() * np.sqrt(252))
        return round(sharpe, 3)

    except Exception as exc:
        logger.warning("execute_and_get_sharpe error: %s", exc)
        return 0.0


def run_walk_forward(
    code: str,
    df: pd.DataFrame,
    n_splits: int = 5,
) -> dict:
    
    if df is None or len(df) < n_splits * 30:
        logger.warning(
            "DataFrame too short for %d-split walk-forward (need ≥%d rows, got %d)",
            n_splits, n_splits * 30, len(df) if df is not None else 0,
        )
        return WalkForwardResult(
            windows=[], avg_oos_sharpe=0.0, consistent=False, n_splits=n_splits
        ).to_dict()

    split_size = len(df) // n_splits
    windows    = []

    logger.info(
        "Walk-forward: %d splits × %d rows each on %d total rows",
        n_splits - 1, split_size, len(df),
    )

    for i in range(n_splits - 1):
        train_end   = (i + 1) * split_size
        test_start  = train_end
        test_end    = (i + 2) * split_size

        train_df = df.iloc[:train_end]
        test_df  = df.iloc[test_start:test_end]

        is_sharpe  = execute_and_get_sharpe(code, train_df)
        oos_sharpe = execute_and_get_sharpe(code, test_df)

        window = WalkForwardWindow(
            window            = i + 1,
            in_sample_sharpe  = is_sharpe,
            out_sample_sharpe = oos_sharpe,
            in_sample_start   = str(train_df.index[0].date()),
            in_sample_end     = str(train_df.index[-1].date()),
            out_sample_start  = str(test_df.index[0].date()),
            out_sample_end    = str(test_df.index[-1].date()),
        )
        windows.append({
            "window":            window.window,
            "in_sample_sharpe":  window.in_sample_sharpe,
            "out_sample_sharpe": window.out_sample_sharpe,
            "in_sample_start":   window.in_sample_start,
            "in_sample_end":     window.in_sample_end,
            "out_sample_start":  window.out_sample_start,
            "out_sample_end":    window.out_sample_end,
        })
        logger.info(
            "Window %d: IS Sharpe=%.3f  OOS Sharpe=%.3f",
            i + 1, is_sharpe, oos_sharpe,
        )

    oos_sharpes  = [w["out_sample_sharpe"] for w in windows]
    avg_oos      = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
    consistent   = avg_oos > 0.5

    result = WalkForwardResult(
        windows        = windows,
        avg_oos_sharpe = avg_oos,
        consistent     = consistent,
        n_splits       = n_splits,
    )

    logger.info(
        "Walk-forward complete: avg OOS Sharpe=%.3f  consistent=%s",
        avg_oos, consistent,
    )
    return result.to_dict()
