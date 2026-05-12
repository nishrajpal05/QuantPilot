"""
Sandbox runner — always uses real vectorbt.

SimplePortfolio / SimpleVbt have been removed. If vectorbt is not installed,
the import below will raise ImportError immediately with a clear message.

To install: pip install vectorbt==0.26.2
"""
import logging
import os
import signal
from contextlib import contextmanager

import pandas as pd

logger = logging.getLogger(__name__)


@contextmanager
def timeout(seconds: int):
    """SIGALRM-based timeout (Unix only). On Windows this is a no-op — rely on the 30s limit instead."""
    def handler(signum, frame):
        raise TimeoutError(f"Backtest exceeded {seconds}s timeout")

    if not hasattr(signal, "SIGALRM"):
        # Windows: no SIGALRM support — just yield without enforcing a hard timeout.
        # vectorbt itself will complete or raise naturally.
        yield
        return

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def execute_strategy(code: str, df: pd.DataFrame, initial_capital: float = 100_000.0) -> object:
    """
    Execute a vectorbt strategy string in a restricted namespace.

    Args:
        code:            Python code string. Must assign result to 'portfolio'.
        df:              OHLCV DataFrame (lowercase cols, DatetimeIndex).
        initial_capital: Starting capital (INR).

    Returns:
        The vectorbt Portfolio object assigned to 'portfolio' in the code.

    Raises:
        ImportError:   If vectorbt is not installed.
        ValueError:    If the code does not assign 'portfolio'.
        TimeoutError:  If execution takes longer than 30 seconds (Unix).
        RuntimeError:  For all other execution failures.
    """
    # Always import real vectorbt — raises ImportError immediately if missing
    try:
        import vectorbt as vbt
        logger.info("vectorbt %s loaded", getattr(vbt, "__version__", "unknown"))
    except ImportError as exc:
        raise ImportError(
            "vectorbt is not installed. Run: pip install vectorbt==0.26.2\n"
            f"Original error: {exc}"
        ) from exc

    namespace = {
        "df": df,
        "pd": pd,
        "vbt": vbt,
        "initial_capital": initial_capital,
    }

    try:
        with timeout(30):
            exec(code, namespace)  # noqa: S102

        if "portfolio" not in namespace:
            raise ValueError(
                "Strategy code must assign the vectorbt Portfolio result to a "
                "variable named 'portfolio'. Check the generated code."
            )

        return namespace["portfolio"]

    except (TimeoutError, ValueError, ImportError):
        raise
    except Exception as e:
        raise RuntimeError(f"Strategy execution failed: {e}") from e
