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
    dsr_score: float        
    equity_curve: List[Dict[str, Any]] 
    trades: List[Dict[str, Any]]       
    audit_hash: str        