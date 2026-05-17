from typing import TypedDict, Optional, Any


class AgentState(TypedDict):
    # ── Inputs ─────────────────────────────────────────────────────────────────
    user_id:         str
    backtest_id:     str
    symbol:          str
    exchange:        str
    start_date:      str
    end_date:        str
    prompt:          str
    initial_capital: float
    resolution:      str        # 'D' | '1min' | '5min' etc.

    # ── Agent outputs (populated as graph progresses) ──────────────────────────
    df:              Optional[Any]    # pd.DataFrame from data_node
    generated_code:  Optional[str]   # from strategy_node
    backtest_result: Optional[dict]  # from backtest_node
    risk_result:     Optional[dict]  # from risk_node (adds monte_carlo, walk_forward)
    compliance:      Optional[dict]  # from compliance_node
    audit_hash:      Optional[str]   # from audit_node

    # ── Control ────────────────────────────────────────────────────────────────
    error:           Optional[str]   # first error — short-circuits remaining nodes
    current_step:    Optional[str]   # e.g. 'data' | 'strategy' | 'backtest' etc.
