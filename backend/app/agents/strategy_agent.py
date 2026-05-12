import os

from groq import Groq

SYSTEM_PROMPT = '''You are a Python quant engineer writing vectorbt backtesting code.
Generate ONLY raw executable Python code. No markdown, no triple-backticks, no explanation.

Available variables (already in scope, do NOT redefine):
  df               — pandas DataFrame with columns: open, high, low, close, volume (all lowercase)
                     Index is a DatetimeIndex (date-only, timezone-naive).
  vbt              — the vectorbt module (version 0.26.2)
  pd               — pandas module
  initial_capital  — float, e.g. 100000.0

Rules you MUST follow:
  1. Compute ALL indicators (RSI, MACD, SMA, EMA, Bollinger etc.) using pure PANDAS operations.
     NEVER use vbt.RSI, vbt.MACD, vbt.indicators, or any vbt indicator class.
  2. Create boolean Series named `entries` and `exits` aligned with df.index.
  3. Build the portfolio with:
       portfolio = vbt.Portfolio.from_signals(
           df["close"], entries, exits, init_cash=initial_capital, freq="1D"
       )
  4. The variable `portfolio` MUST exist when the code finishes.
  5. Do not import any libraries — they are already imported.

Example RSI pattern (use this exact pandas approach):
  delta = df["close"].diff()
  gain = delta.clip(lower=0).rolling(14).mean()
  loss = (-delta.clip(upper=0)).rolling(14).mean()
  rsi = 100 - 100 / (1 + gain / loss.replace(0, 1e-9))
  entries = rsi < 30
  exits   = rsi > 70
  portfolio = vbt.Portfolio.from_signals(df["close"], entries, exits, init_cash=initial_capital, freq="1D")
'''


def generate_strategy_code(prompt: str, api_key: str) -> str:
    """
    Calls Groq API (llama3-70b-8192) to convert a plain-English trading
    strategy description into executable vectorbt Python code.

    Falls back to GROQ_API_KEY_FALLBACK env var on RateLimitError.

    Args:
        prompt:  Plain-English strategy description from the user.
        api_key: Primary Groq API key (from request context / env var).

    Returns:
        Raw vectorbt Python code string ready for sandbox execution.

    Raises:
        RuntimeError: If all Groq API keys are exhausted or fail, and
                      QP_USE_LIVE_DATA=1 is set (no local fallback allowed).
    """
    primary = api_key or os.getenv("GROQ_API_KEY")
    fallback = os.getenv("GROQ_API_KEY_FALLBACK", "")
    use_live = os.getenv("QP_USE_LIVE_DATA", "").lower() in {"1", "true", "yes"}

    keys = [
        key for key in [primary, fallback]
        if key and "xxxxxxxx" not in key.lower() and not key.lower().startswith("your-")
    ]

    last_exc = None
    for key in keys:
        try:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=1024,
                temperature=0.1,
            )
            code = resp.choices[0].message.content.strip()
            # Strip markdown fences if model wraps in ```python ... ```
            if code.startswith("```"):
                lines = code.splitlines()
                code = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                ).strip()
            return code

        except Exception as e:
            last_exc = e
            if "rate" in str(e).lower() and fallback:
                continue
            # Non-rate-limit error — break immediately
            break

    # When QP_USE_LIVE_DATA=1 is set, refuse to silently fall back to local code
    if use_live:
        raise RuntimeError(
            f"Groq API failed — cannot generate strategy code. "
            f"Check GROQ_API_KEY and internet connectivity.\n"
            f"Error: {last_exc}"
        )

    # Development-only fallback (no QP_USE_LIVE_DATA env set)
    return generate_local_strategy_code(prompt)


def generate_local_strategy_code(prompt: str) -> str:
    """
    Local fallback when Groq credentials or network access are unavailable
    AND QP_USE_LIVE_DATA is NOT set.
    Uses real vectorbt (vbt variable injected by runner.py).
    """
    lower_prompt = prompt.lower()
    if "rsi" in lower_prompt:
        return """
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
""".strip()

    return """
fast = df['close'].rolling(20, min_periods=20).mean()
slow = df['close'].rolling(50, min_periods=50).mean()
entries = (fast > slow) & (fast.shift(1) <= slow.shift(1))
exits = (fast < slow) & (fast.shift(1) >= slow.shift(1))
portfolio = vbt.Portfolio.from_signals(
    df['close'], entries, exits, init_cash=initial_capital, freq='1D'
)
""".strip()
