"""
Full end-to-end backtest test with real data + real vectorbt.
Run from project root: python _test_backtest.py
"""
import sys, os
sys.path.insert(0, 'backend')
os.environ['QP_USE_LIVE_DATA'] = '1'
os.environ['QP_USE_VECTORBT'] = '1'

# Load .env manually for DB URL etc
from dotenv import load_dotenv
load_dotenv('backend/.env')

print("=" * 60)
print("STEP 1 — Real data fetch (yfinance)")
print("=" * 60)
from app.data.ingest import fetch_from_yfinance
df = fetch_from_yfinance('RELIANCE', '2020-01-01', '2024-12-31', 'NSE')
print(f"  Rows        : {len(df)}")
print(f"  Columns     : {list(df.columns)}")
print(f"  data_source : {df.attrs.get('data_source')}")
assert len(df) > 0, "FAIL: No rows returned"
assert df.attrs.get('data_source') != 'sample', "FAIL: Got sample data"
df.attrs['rows_used'] = len(df)
print("  PASS\n")

print("=" * 60)
print("STEP 2 — Real vectorbt execution")
print("=" * 60)
from app.sandbox.runner import execute_strategy

rsi_code = """
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(14, min_periods=14).mean()
avg_loss = loss.rolling(14, min_periods=14).mean()
rs = avg_gain / avg_loss.replace(0, 1e-9)
rsi = 100 - (100 / (1 + rs))
entries = rsi < 30
exits = rsi > 70
portfolio = vbt.Portfolio.from_signals(
    df['close'], entries, exits, init_cash=initial_capital, freq='1D'
)
"""

portfolio = execute_strategy(rsi_code, df, initial_capital=100_000.0)
print(f"  Portfolio type  : {type(portfolio).__name__}")
equity = portfolio.value()
print(f"  Equity rows     : {len(equity)}")
print(f"  Final equity    : Rs {equity.iloc[-1]:,.2f}")
print("  PASS\n")

print("=" * 60)
print("STEP 3 — Full BacktestResult (run_backtest)")
print("=" * 60)
from app.agents import run_backtest
result = run_backtest(
    code=rsi_code,
    df=df,
    initial_capital=100_000.0,
    symbol='RELIANCE',
    start='2020-01-01',
    end='2024-12-31',
)
print(f"  total_return_pct : {result.total_return_pct}%")
print(f"  cagr             : {result.cagr}%")
print(f"  sharpe_ratio     : {result.sharpe_ratio}")
print(f"  max_drawdown_pct : {result.max_drawdown_pct}%")
print(f"  total_trades     : {result.total_trades}")
print(f"  data_source      : {result.data_source}")
print(f"  rows_used        : {result.rows_used}")
print(f"  audit_hash       : {result.audit_hash[:16]}...")
assert result.data_source == 'yfinance', f"FAIL: data_source={result.data_source}"
assert result.rows_used > 0, "FAIL: rows_used=0"
print("  PASS\n")

print("=" * 60)
print("ALL TESTS PASSED — Real data + Real vectorbt confirmed")
print("=" * 60)
