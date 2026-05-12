"""
API-level E2E test: register -> login -> submit backtest -> poll until done -> verify data_source
Run from project root: python _test_api.py
"""
import time
import urllib.request
import urllib.error
import os
import json

# Override with TEST_API_URL env var to test production:
#   TEST_API_URL=https://quantpilot-po4m.onrender.com python _test_api.py
BASE = os.getenv("TEST_API_URL", "http://127.0.0.1:8000").rstrip("/") + "/api/v1"

def post(path, body, token=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {})
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path, token=None):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"} if token else {}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("=" * 60)
print("STEP 1 — Register")
print("=" * 60)
status, body = post("/auth/register", {
    "full_name": "DefinitiveTest",
    "email": "definitivetest_qp@gmail.com",
    "password": "Test@12345"
})
print(f"  Status: {status}  Body: {body}")
if status not in (200, 201, 400):  # 400 = already registered
    raise SystemExit(f"FAIL: unexpected register status {status}")

print()
print("=" * 60)
print("STEP 2 — Login")
print("=" * 60)
status, body = post("/auth/login", {
    "email": "definitivetest_qp@gmail.com",
    "password": "Test@12345"
})
print(f"  Status: {status}")
assert status == 200, f"FAIL: login returned {status}: {body}"
token = body.get("access_token")
assert token, "FAIL: No access_token in response"
print(f"  Token: {token[:20]}...  PASS")

print()
print("=" * 60)
print("STEP 3 — Submit backtest (RELIANCE RSI, 2022-2024)")
print("=" * 60)
status, body = post("/backtest", {
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "start_date": "2022-01-01",
    "end_date": "2024-12-31",
    "prompt": "RSI strategy: buy when RSI drops below 30, sell when RSI goes above 70",
    "initial_capital": 100000.0
}, token=token)
print(f"  Status: {status}  Body: {body}")
assert status == 202, f"FAIL: Expected 202, got {status}: {body}"
backtest_id = body.get("backtest_id")
assert backtest_id, "FAIL: No backtest_id in response"
print(f"  backtest_id: {backtest_id}  PASS")

print()
print("=" * 60)
print("STEP 4 — Poll until completed (max 3 min)")
print("=" * 60)
deadline = time.time() + 180
result = None
while time.time() < deadline:
    status, result = get(f"/backtest/{backtest_id}", token=token)
    bstatus = result.get("status")
    print(f"  [{int(time.time() % 1000)}] status={bstatus}", flush=True)
    if bstatus == "completed":
        print("  Backtest COMPLETED")
        break
    if bstatus == "failed":
        print(f"  FAILED: {result.get('error_message')}")
        raise SystemExit("Backtest failed")
    time.sleep(8)
else:
    raise SystemExit("TIMEOUT: backtest did not complete in 3 minutes")

print()
print("=" * 60)
print("STEP 5 — Verify result fields")
print("=" * 60)
data_source = result.get("data_source")
rows_used   = result.get("rows_used")
total_ret   = result.get("total_return_pct")
sharpe      = result.get("sharpe_ratio")
trades      = result.get("total_trades")

print(f"  data_source      : {data_source}")
print(f"  rows_used        : {rows_used}")
print(f"  total_return_pct : {total_ret}%")
print(f"  sharpe_ratio     : {sharpe}")
print(f"  total_trades     : {trades}")

assert data_source in ("yfinance", "nsepy", "cache"), \
    f"FAIL: data_source={data_source!r} — must be yfinance/nsepy/cache"
assert data_source != "sample", "FAIL: got sample data in live mode"
assert rows_used and rows_used > 0, "FAIL: rows_used is 0 or missing"

print()
print("=" * 60)
print(f"ALL API TESTS PASSED")
print(f"  Data source : {data_source}")
print(f"  Rows used   : {rows_used}")
print(f"  Return      : {total_ret}%")
print("=" * 60)
