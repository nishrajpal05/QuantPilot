

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.data import get_ohlcv
from app.agents import generate_strategy_code, run_backtest
from app.agents.risk_agent import compute_metrics, run_monte_carlo, run_walk_forward
from app.agents.audit_agent import generate_audit_hash
from app.sandbox.runner import execute_strategy

if TYPE_CHECKING:
    from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)



def _guarded(state: "AgentState") -> bool:
    """Return True if an upstream error already occurred (skip this node)."""
    return bool(state.get("error"))

def data_node(state: "AgentState") -> "AgentState":
   
    if _guarded(state):
        return state

    logger.info("[data_node] Fetching %s %s → %s",
                state["symbol"], state["start_date"], state["end_date"])
    try:
        df = get_ohlcv(
            symbol=state["symbol"],
            start=state["start_date"],
            end=state["end_date"],
        )
        if df is None or df.empty:
            raise ValueError(f"No data returned for {state['symbol']}")

        logger.info("[data_node] Fetched %d rows", len(df))
        return {**state, "df": df}

    except Exception as exc:
        logger.error("[data_node] Failed: %s", exc)
        return {**state, "error": f"Data fetch failed: {exc}"}

def strategy_node(state: "AgentState") -> "AgentState":
  
    if _guarded(state):
        return state

    prompt = state["prompt"]

    # Multi-turn refinement: include existing code as context
    if state.get("generated_code"):
        prompt = (
            f"Here is the current strategy code:\n\n"
            f"```python\n{state['generated_code']}\n```\n\n"
            f"User refinement request: {state['prompt']}\n\n"
            f"Generate an updated version of the code incorporating the requested changes. "
            f"Return ONLY executable vectorbt Python code, no explanation."
        )
        logger.info("[strategy_node] Refinement mode — updating existing code")
    else:
        logger.info("[strategy_node] Generating strategy for prompt: %s", prompt[:80])

    try:
        code = generate_strategy_code(prompt, api_key=None)
        logger.info("[strategy_node] Generated %d chars of code", len(code))
        return {**state, "generated_code": code}

    except Exception as exc:
        logger.error("[strategy_node] Failed: %s", exc)
        return {**state, "error": f"Strategy generation failed: {exc}"}


def backtest_node(state: "AgentState") -> "AgentState":

    if _guarded(state):
        return state

    logger.info("[backtest_node] Running backtest — capital %.0f", state["initial_capital"])
    try:
        result = run_backtest(
            code=state["generated_code"],
            df=state["df"],
            initial_capital=state["initial_capital"],
            symbol=state["symbol"],
            start=state["start_date"],
            end=state["end_date"],
        )
        result_dict = result.__dict__
        logger.info(
            "[backtest_node] Done — return=%.2f%% sharpe=%.3f trades=%d",
            result_dict["total_return_pct"],
            result_dict["sharpe_ratio"],
            result_dict["total_trades"],
        )
        return {**state, "backtest_result": result_dict}

    except TimeoutError:
        msg = "Backtest timed out after 30 seconds — simplify the strategy"
        logger.error("[backtest_node] %s", msg)
        return {**state, "error": msg}

    except Exception as exc:
        logger.error("[backtest_node] Failed: %s", exc)
        return {**state, "error": f"Backtest failed: {exc}"}




def risk_node(state: "AgentState") -> "AgentState":

    if _guarded(state):
        return state

    logger.info("[risk_node] Running Monte Carlo + walk-forward analysis")
    try:
        equity_curve = state["backtest_result"]["equity_curve"]
        mc = run_monte_carlo(equity_curve, n_simulations=1000, n_days=252)
        logger.info(
            "[risk_node] MC — median=%.3f P5=%.3f P95=%.3f prob_profit=%.2f%%",
            mc["median_return"], mc["percentile_5"],
            mc["percentile_95"], mc["prob_profit"] * 100,
        )
    except Exception as exc:
        logger.warning("[risk_node] Monte Carlo failed (non-fatal): %s", exc)
        mc = {"error": str(exc)}

    try:
        wf = run_walk_forward(state["generated_code"], state["df"], n_splits=5)
        logger.info(
            "[risk_node] Walk-forward — avg OOS Sharpe=%.3f consistent=%s",
            wf["avg_oos_sharpe"], wf["consistent"],
        )
    except Exception as exc:
        logger.warning("[risk_node] Walk-forward failed (non-fatal): %s", exc)
        wf = {"error": str(exc)}

    risk_result = {
        **state["backtest_result"],
        "monte_carlo": mc,
        "walk_forward": wf,
    }
    return {**state, "risk_result": risk_result}




def compliance_node(state: "AgentState") -> "AgentState":

    if _guarded(state):
        return state

    logger.info("[compliance_node] Checking SEBI compliance")
    try:
        # Try Account 5's real implementation first
        from app.rag import check_compliance  # type: ignore
        compliance = check_compliance(state["prompt"], state["generated_code"])

    except ImportError:
        # Stub until Account 5 is merged — keeps pipeline functional
        logger.warning("[compliance_node] app.rag not available — using stub")
        compliance = _stub_compliance(state["prompt"], state["generated_code"])

    except Exception as exc:
        logger.error("[compliance_node] Compliance check failed: %s", exc)
        compliance = {
            "compliant": None,
            "issues": [f"Compliance check error: {exc}"],
            "algo_id": None,
            "checked_at": None,
        }

    return {**state, "compliance": compliance}


def _stub_compliance(prompt: str, code: str) -> dict:
    """Minimal rule engine — active until Account 5 (rag-compliance) is merged."""
    import hashlib
    from datetime import datetime, timezone

    BANNED = ["crypto", "forex", "commodity"]
    LEVERAGE_KEYWORDS = ["margin", "leverage", "short_sell"]
    HFT_KEYWORDS = ["minute", "tick", "second"]

    issues = []
    for inst in BANNED:
        if inst in prompt.lower():
            issues.append(f"Banned instrument: '{inst}' not supported for algo trading")

    if any(kw in code.lower() for kw in LEVERAGE_KEYWORDS):
        issues.append("Leverage/short-selling requires additional SEBI registration")

    if any(kw in prompt.lower() for kw in HFT_KEYWORDS):
        issues.append("HFT strategies require SEBI algo trading approval (SEBI circular 2022)")

    payload = f"QP-{prompt[:50]}-{code[:50]}"
    algo_id = "ALGO-" + hashlib.md5(payload.encode()).hexdigest()[:12].upper()

    return {
        "compliant": len(issues) == 0,
        "issues": issues,
        "algo_id": algo_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

def audit_node(state: "AgentState") -> "AgentState":

    if _guarded(state):
        return state

    logger.info("[audit_node] Generating audit hash")
    try:
        audit_hash = generate_audit_hash(
            symbol=state["symbol"],
            start=state["start_date"],
            end=state["end_date"],
            code=state["generated_code"],
            results=state["risk_result"],
        )
        logger.info("[audit_node] Hash: %s…", audit_hash[:16])
        return {**state, "audit_hash": audit_hash}

    except Exception as exc:

        logger.error("[audit_node] Audit hash failed (non-fatal): %s", exc)
        return {**state, "audit_hash": None}
