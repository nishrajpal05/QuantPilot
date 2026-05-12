import os

from groq import Groq

SYSTEM_PROMPT = '''You are a Python quant engineer.
Generate ONLY executable vectorbt code. No markdown, no explanation.
The DataFrame 'df' is already available with columns:
open, high, low, close, volume (lowercase). Index is DatetimeIndex.
Use vectorbt Portfolio.from_signals() or Portfolio.from_order_func().
Store the portfolio in a variable named 'portfolio'.'''


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
        RuntimeError: If all Groq API keys are exhausted or fail.
    """
    primary = api_key or os.getenv("GROQ_API_KEY")
    fallback = os.getenv("GROQ_API_KEY_FALLBACK", "")

    for key in filter(None, [primary, fallback]):
        try:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=1024,
                temperature=0.1,
            )
            return resp.choices[0].message.content.strip()

        except Exception as e:
            if "rate" in str(e).lower() and fallback:
                continue
            raise

    raise RuntimeError("All Groq API keys exhausted")
