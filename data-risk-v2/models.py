from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BacktestResult:
   
    total_return_pct:  float
    cagr:              float
    sharpe_ratio:      float
    max_drawdown_pct:  float
    win_rate:          float
    total_trades:      int
    dsr_score:         float        # Deflated Sharpe Ratio — > 0.5 = not overfit
    equity_curve:      list         # [{'date': 'YYYY-MM-DD', 'value': float}, ...]
    trades:            list         # [{'entry_date', 'exit_date', 'pnl'}, ...]
    audit_hash:        str          # SHA-256(symbol+start+end+code+results)

    # Phase 2 additions — populated by RiskAgent, optional for Phase 1 compat
    monte_carlo:       Optional[dict] = None   # MonteCarloResult as dict
    walk_forward:      Optional[dict] = None   # WalkForwardResult as dict
    drawdown_periods:  Optional[list] = None   # [{start, trough, end, pct, days}, ...]
    compliance:        Optional[dict] = None   # from ComplianceAgent


@dataclass
class MonteCarloResult:

    median_return:  float
    percentile_5:   float
    percentile_95:  float
    prob_profit:    float           # 0.0 → 1.0
    simulations:    list            # list of 100 paths, each path = list of floats
    n_simulations:  int = 1000
    n_days:         int = 252

    def to_dict(self) -> dict:
        return {
            "median_return":  round(self.median_return, 4),
            "percentile_5":   round(self.percentile_5, 4),
            "percentile_95":  round(self.percentile_95, 4),
            "prob_profit":    round(self.prob_profit, 4),
            "simulations":    [
                [round(v, 4) for v in path] for path in self.simulations
            ],
            "n_simulations":  self.n_simulations,
            "n_days":         self.n_days,
        }


@dataclass
class WalkForwardWindow:
   
    window:            int
    in_sample_sharpe:  float
    out_sample_sharpe: float
    in_sample_start:   str         # 'YYYY-MM-DD'
    in_sample_end:     str
    out_sample_start:  str
    out_sample_end:    str


@dataclass
class WalkForwardResult:
  
    windows:        list           
    avg_oos_sharpe: float
    consistent:     bool            
    n_splits:       int = 5

    def to_dict(self) -> dict:
        return {
            "windows":        self.windows,
            "avg_oos_sharpe": round(self.avg_oos_sharpe, 3),
            "consistent":     self.consistent,
            "n_splits":       self.n_splits,
            "verdict":        (
                "Strategy generalises well to unseen data."
                if self.consistent else
                "Strategy may be over-optimised — out-of-sample performance is weak."
            ),
        }
