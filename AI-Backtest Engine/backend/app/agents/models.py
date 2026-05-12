from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class BacktestResult:
    total_return_pct: float
    cagr: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    dsr_score: float        # Deflated Sharpe Ratio, >0.5 = not overfit
    equity_curve: List[Dict[str, Any]]  # [{'date': 'YYYY-MM-DD', 'value': float}, ...]
    trades: List[Dict[str, Any]]        # [{'entry_date', 'exit_date', 'pnl'}, ...]
    audit_hash: str         # SHA-256(symbol+start+end+code+results)
