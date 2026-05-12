import sys, os
sys.path.insert(0, 'backend')
os.environ['QP_USE_LIVE_DATA'] = '1'
os.environ['QP_USE_VECTORBT'] = '1'

print('=== Testing fetch_from_yfinance ===')
from app.data.ingest import fetch_from_yfinance
df = fetch_from_yfinance('RELIANCE', '2023-01-01', '2024-01-01', 'NSE')
print('Rows:', len(df))
print('Columns:', list(df.columns))
src = df.attrs.get('data_source')
print('data_source:', src)
assert len(df) > 0, 'Expected rows > 0'
assert src != 'sample', 'data_source must not be sample'
print('Head:')
print(df.head(3).to_string())
print()
print('=== yfinance: PASS ===')
