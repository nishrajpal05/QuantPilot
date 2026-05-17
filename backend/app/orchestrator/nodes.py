"""
LangGraph node functions.
Each node receives AgentState, does one job, returns updated state.
If it sets state['error'], downstream nodes are skipped.
"""
from app.orchestrator.state import AgentState


# ── Data node ──────────────────────────────────────────────────────────────────

def data_node(state: AgentState) -> AgentState:
    """Fetch OHLCV data — Account 2 module."""
    try:
        from app.data import get_ohlcv, get_ohlcv_intraday

        resolution = state.get("resolution", "D")
        if resolution == "D":
            df = get_ohlcv(
                state["symbol"],
                state["start_date"],
                state["end_date"],
                state.get("exchange", "NSE"),
            )
        else:
            df = get_ohlcv_intraday(
                state["symbol"],
                resolution,
                state["start_date"],
                state["end_date"],
                state["user_id"],
            )

        if df is None or df.empty:
            return {**state, "error": f"No data found for {state['symbol']} ({state['start_date']} to {state['end_date']})", "current_step": "data"}

        return {**state, "df": df, "current_step": "data"}

    except ImportError:
        return {**state, "error": "Data module not available — merge data-risk-v2 branch first.", "current_step": "data"}
    except Exception as e:
        return {**state, "error": f"Data fetch failed: {str(e)}", "current_step": "data"}


# ── Strategy node ──────────────────────────────────────────────────────────────

def strategy_node(state: AgentState) -> AgentState:
    """NL → vectorbt code — Account 3 module."""
    if state.get("error"):
        return state
    try:
        from app.agents import generate_strategy_code
        from app.core.config import get_settings

        settings = get_settings()
        code = generate_strategy_code(
            state["prompt"],
            api_key=settings.groq_api_key,
        )
        return {**state, "generated_code": code, "current_step": "strategy"}

    except ImportError:
        return {**state, "error": "Agents module not available — merge ai-agents-v2 branch first.", "current_step": "strategy"}
    except Exception as e:
        return {**state, "error": f"Strategy generation failed: {str(e)}", "current_step": "strategy"}


# ── Backtest node ──────────────────────────────────────────────────────────────

def backtest_node(state: AgentState) -> AgentState:
    """Execute strategy code in sandbox — Account 3 module."""
    if state.get("error"):
        return state
    try:
        from app.agents import run_backtest

        result = run_backtest(
            state["generated_code"],
            state["df"],
            state["initial_capital"],
        )
        return {**state, "backtest_result": result.__dict__, "current_step": "backtest"}

    except Exception as e:
        return {**state, "error": f"Backtest execution failed: {str(e)}", "current_step": "backtest"}


# ── Risk node ──────────────────────────────────────────────────────────────────

def risk_node(state: AgentState) -> AgentState:
    """Monte Carlo + walk-forward — Account 2 module."""
    if state.get("error"):
        return state
    try:
        from app.agents.risk_agent import run_monte_carlo, run_walk_forward

        result = dict(state["backtest_result"])

        # Monte Carlo on equity curve
        mc = run_monte_carlo(result.get("equity_curve", []))
        result["monte_carlo"] = mc

        # Walk-forward on raw data + code
        wf = run_walk_forward(state["generated_code"], state["df"])
        result["walk_forward"] = wf

        return {**state, "risk_result": result, "current_step": "risk"}

    except ImportError:
        # Risk upgrade not merged yet — pass through base result
        return {**state, "risk_result": state["backtest_result"], "current_step": "risk"}
    except Exception as e:
        # Non-fatal — don't fail the whole backtest for risk extras
        return {**state, "risk_result": state["backtest_result"], "current_step": "risk"}


# ── Compliance node ────────────────────────────────────────────────────────────

def compliance_node(state: AgentState) -> AgentState:
    """SEBI rule check — Account 5 module."""
    if state.get("error"):
        return state
    try:
        from app.agents.compliance_agent import check_compliance

        compliance = check_compliance(
            state["prompt"],
            state.get("generated_code", ""),
        )
        return {**state, "compliance": compliance, "current_step": "compliance"}

    except ImportError:
        # Compliance not merged yet — return neutral result
        return {**state, "compliance": {
            "compliant": True,
            "issues": [],
            "algo_id": None,
            "note": "Compliance module pending — rag-compliance branch not merged",
        }, "current_step": "compliance"}
    except Exception as e:
        return {**state, "compliance": {
            "compliant": None,
            "issues": [str(e)],
            "algo_id": None,
        }, "current_step": "compliance"}


# ── Audit node ─────────────────────────────────────────────────────────────────

def audit_node(state: AgentState) -> AgentState:
    """Generate Merkle audit hash."""
    if state.get("error"):
        return state
    try:
        from app.agents.audit_agent import generate_audit_hash

        risk_result = state.get("risk_result") or state.get("backtest_result") or {}
        audit_hash = generate_audit_hash(
            state["symbol"],
            state["start_date"],
            state["end_date"],
            state.get("generated_code", ""),
            risk_result,
        )
        return {**state, "audit_hash": audit_hash, "current_step": "audit"}

    except ImportError:
        # Fallback: compute hash inline if audit_agent not merged
        import hashlib, json
        payload = json.dumps({
            "symbol": state["symbol"],
            "start": state["start_date"],
            "end": state["end_date"],
        }, sort_keys=True)
        fallback_hash = hashlib.sha256(payload.encode()).hexdigest()
        return {**state, "audit_hash": fallback_hash, "current_step": "audit"}
    except Exception as e:
        return {**state, "audit_hash": "", "current_step": "audit"}
