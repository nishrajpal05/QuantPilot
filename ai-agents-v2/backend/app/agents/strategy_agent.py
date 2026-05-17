

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)


STRATEGY_SYSTEM_PROMPT = """You are an expert Python quant engineer specialising in the Indian stock market.

Generate ONLY executable vectorbt code. No markdown fences, no comments, no explanation.

Environment contract:
- DataFrame 'df' is available with columns: open, high, low, close, volume (lowercase).
- Index is a pandas DatetimeIndex (daily OHLCV bars from NSE/BSE).
- 'vbt' (vectorbt) and 'pd' (pandas) are imported in the namespace.
- Store the final portfolio in a variable named exactly: portfolio
- Use vectorbt Portfolio.from_signals() or Portfolio.from_order_func().
- Do NOT use plt.show(), print(), or any I/O — pure computation only.

NSE/BSE rules:
- Equities only (no crypto, forex, commodity in the generated code).
- Lot size = 1 for equity delivery.
- Use 0.1% brokerage cost via: fees=0.001 in Portfolio.from_signals().
"""

REFINEMENT_SYSTEM_PROMPT = """You are an expert Python quant engineer reviewing and improving existing vectorbt trading strategy code.

The user wants to refine the strategy. You will receive:
1. The current Python code
2. The user's refinement request

Return ONLY the updated executable Python code — no explanation, no markdown.
Apply the requested change conservatively and keep all other logic intact.
The portfolio must still be assigned to the variable named 'portfolio'.
"""

EXPLANATION_SYSTEM_PROMPT = """You are a trading strategy analyst. A user will show you vectorbt Python code.
Explain what the strategy does in plain English — no code, no jargon.
Structure your explanation as:
1. Entry signal: what triggers a buy
2. Exit signal: what triggers a sell
3. Risk controls: any stops or position sizing
4. Best suited for: trending / ranging / volatile markets
Keep it under 150 words. Be direct and precise."""



def _get_keys(api_key: Optional[str]) -> list:
    """Return a priority-ordered list of non-empty Groq API keys."""
    candidates = [
        api_key,
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY_FALLBACK"),
    ]
    return [k for k in candidates if k]


def _call_groq(
    messages: list,
    api_key: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
    max_retries: int = 3,
) -> str:
  
    keys = _get_keys(api_key)
    if not keys:
        raise RuntimeError("No Groq API keys configured — set GROQ_API_KEY env var")

    last_exc = RuntimeError("Unknown error")

    for key in keys:
        client = Groq(api_key=key)
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return resp.choices[0].message.content.strip()

            except Exception as exc:
                last_exc = exc
                err_str = str(exc).lower()

                if "rate" in err_str:
                    logger.warning("[strategy_agent] Rate limit on key ...%s — rotating", key[-4:])
                    break

                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "[strategy_agent] Transient error (attempt %d/%d): %s — retrying in %ds",
                        attempt, max_retries, exc, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("[strategy_agent] All retries exhausted for key ...%s", key[-4:])

    raise RuntimeError(f"All Groq API keys exhausted. Last error: {last_exc}")


def generate_strategy_code(prompt: str, api_key: Optional[str] = None) -> str:

    logger.info("[strategy_agent] Generating strategy code (%d chars prompt)", len(prompt))

    messages = [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]
    code = _call_groq(messages, api_key=api_key, max_tokens=1024, temperature=0.1)
    logger.info("[strategy_agent] Generated %d chars of code", len(code))
    return code


def refine_strategy_code(
    existing_code: str,
    refinement_request: str,
    api_key: Optional[str] = None,
) -> str:

    logger.info("[strategy_agent] Refining strategy: '%s'", refinement_request[:80])
    messages = [
        {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Current strategy code:\n\n```python\n{existing_code}\n```\n\n"
                f"Refinement request: {refinement_request}"
            ),
        },
    ]
    code = _call_groq(messages, api_key=api_key, max_tokens=1024, temperature=0.1)
    logger.info("[strategy_agent] Refined code: %d chars", len(code))
    return code


def explain_strategy(code: str, api_key: Optional[str] = None) -> str:
    logger.info("[strategy_agent] Generating strategy explanation")
    messages = [
        {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
        {"role": "user",   "content": f"Explain this strategy:\n\n```python\n{code}\n```"},
    ]
    explanation = _call_groq(messages, api_key=api_key, max_tokens=300, temperature=0.3)
    logger.info("[strategy_agent] Explanation: %d chars", len(explanation))
    return explanation
