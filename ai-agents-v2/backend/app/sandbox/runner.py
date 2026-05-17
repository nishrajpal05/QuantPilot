import signal
import pandas as pd
from contextlib import contextmanager


# ── Timeout context manager ────────────────────────────────────────────────────

@contextmanager
def timeout(seconds: int):
    def handler(signum, frame):
        raise TimeoutError(f"Backtest exceeded {seconds}s timeout")

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)   # Always cancel the alarm on exit


# ── Safe strategy executor ─────────────────────────────────────────────────────

def execute_strategy(code: str, df: pd.DataFrame) -> object:
  
    namespace = {"df": df, "pd": pd}

    try:
        import vectorbt as vbt
        namespace["vbt"] = vbt

        with timeout(30):
            exec(code, namespace)  # noqa: S102

        if "portfolio" not in namespace:
            raise ValueError(
                "Code must assign the vectorbt result to a variable named 'portfolio'"
            )

        return namespace["portfolio"]

    except TimeoutError:
        raise  # Re-raise as-is so caller can report 'timeout' status

    except ValueError:
        raise  # Re-raise as-is for missing 'portfolio' case

    except Exception as e:
        raise RuntimeError(f"Strategy execution failed: {e}") from e
