import hashlib
import json


def generate_audit_hash(
    symbol: str,
    start: str,
    end: str,
    code: str,
    results: dict,
) -> str:
    """
    Generate a tamper-proof SHA-256 audit hash for a completed backtest.

    The hash binds together the input parameters (symbol, date range, strategy
    code) and the key output metrics.  Any change to inputs or results will
    produce a completely different hash, making silent manipulation detectable.

    Args:
        symbol:  Ticker symbol used in the backtest (e.g. 'RELIANCE').
        start:   Start date string 'YYYY-MM-DD'.
        end:     End date string 'YYYY-MM-DD'.
        code:    The exact vectorbt Python code that was executed.
        results: Dict containing at minimum total_return_pct, sharpe_ratio,
                 and total_trades (as returned by risk_agent.compute_metrics).

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.
    """
    payload = json.dumps(
        {
            "symbol": symbol,
            "start": start,
            "end": end,
            "code": code,
            "total_return_pct": results["total_return_pct"],
            "sharpe_ratio": results["sharpe_ratio"],
            "total_trades": results["total_trades"],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
