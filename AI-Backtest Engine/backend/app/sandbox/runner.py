import signal
import pandas as pd
from contextlib import contextmanager


# ── Timeout context manager ────────────────────────────────────────────────────

@contextmanager
def timeout(seconds: int):
    """
    UNIX signal-based timeout.  Raises TimeoutError if the block takes
    longer than `seconds`.

    Note: signal.SIGALRM is only available on Linux/macOS.
    This is compatible with Render's Linux execution environment.
    """
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
    """
    Execute LLM-generated vectorbt strategy code safely inside a sandboxed
    namespace with a hard 30-second timeout.

    The executed code receives:
        df  — the OHLCV DataFrame (lowercase columns, DatetimeIndex)
        pd  — pandas
        vbt — vectorbt

    The code MUST assign its vectorbt Portfolio to a variable named
    'portfolio' in the global namespace, or a ValueError is raised.

    Args:
        code: Raw Python code string (from strategy_agent.generate_strategy_code).
        df:   OHLCV DataFrame prepared by Account 2's get_ohlcv().

    Returns:
        vectorbt Portfolio object for metric computation.

    Raises:
        TimeoutError:  If execution exceeds 30 seconds.
        ValueError:    If the code does not assign a 'portfolio' variable.
        RuntimeError:  For any other execution-time error, with detail message.
    """
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
