# QuantPilot — DEV 3: AI + Backtest Engine

**Branch:** `ai-backtest-engine`

This module is the intelligence core of QuantPilot. It converts plain-English trading strategies into executable vectorbt code, runs them safely, computes comprehensive risk metrics, and generates tamper-proof audit hashes.

## Module Structure

```
backend/app/
├── agents/
│   ├── __init__.py         ← Public API: generate_strategy_code, run_backtest
│   ├── models.py           ← BacktestResult dataclass
│   ├── strategy_agent.py   ← Groq API: NL → vectorbt code
│   ├── risk_agent.py       ← Sharpe, CAGR, drawdown, DSR, walk-forward
│   └── audit_agent.py      ← SHA-256 Merkle audit hash
└── sandbox/
    ├── __init__.py         ← Empty
    └── runner.py           ← Safe exec() with 30s timeout
```

## Public API (imported by Account 1)

```python
from app.agents import generate_strategy_code, run_backtest
```

### `generate_strategy_code(prompt: str, api_key: str) -> str`
Calls Groq (llama3-70b-8192) to convert a plain-English strategy into vectorbt Python code. Falls back to `GROQ_API_KEY_FALLBACK` on rate limit errors.

### `run_backtest(code, df, initial_capital, symbol, start, end) -> BacktestResult`
Executes the strategy in a sandboxed namespace (30s timeout), computes risk metrics, and returns a `BacktestResult` dataclass.

## Environment Variables Required

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Primary Groq API key |
| `GROQ_API_KEY_FALLBACK` | Fallback Groq key for rate limiting |

> Do **not** import from `app.core` — use `os.getenv()` directly.

## BacktestResult Fields

| Field | Type | Description |
|---|---|---|
| `total_return_pct` | float | Total return percentage |
| `cagr` | float | Compound Annual Growth Rate % |
| `sharpe_ratio` | float | Annualised Sharpe Ratio |
| `max_drawdown_pct` | float | Maximum drawdown % (negative) |
| `win_rate` | float | Fraction of winning trades (0–1) |
| `total_trades` | int | Number of completed trades |
| `dsr_score` | float | Deflated Sharpe Ratio (>0.5 = not overfit) |
| `equity_curve` | list | `[{date, value}, ...]` |
| `trades` | list | `[{entry_date, exit_date, pnl}, ...]` |
| `audit_hash` | str | SHA-256 hex digest |

## Git Workflow

```bash
# Clone the repo (Account 1 creates it)
git clone https://github.com/YOU/quantpilot && cd quantpilot
git checkout -b ai-backtest-engine

# Build and commit
git add backend/app/agents/ backend/app/sandbox/
git commit -m "feat(account3): AI backtest engine — strategy agent, risk metrics, audit hash"
git push origin ai-backtest-engine
```

Account 1 merges this branch into `main` after all accounts are complete.
