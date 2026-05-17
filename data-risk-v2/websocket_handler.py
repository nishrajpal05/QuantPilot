import json
import logging
import os
import threading

import redis

logger = logging.getLogger(__name__)

# Redis client — shared across the module
_redis_client = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client



def on_message(message):
   
    if not message:
        return

    ticks = message if isinstance(message, list) else [message]
    r = _get_redis()

    pipe = r.pipeline()
    for tick in ticks:
        symbol = tick.get("symbol", "")
        if not symbol:
            continue

        payload = json.dumps({
            "ltp":    tick.get("ltp"),
            "open":   tick.get("open_price"),
            "high":   tick.get("high_price"),
            "low":    tick.get("low_price"),
            "volume": tick.get("vol_traded_today"),
            "ts":     tick.get("timestamp"),
            "change": tick.get("ch"),
            "chp":    tick.get("chp"),      # change percent
        })

        # TTL = 60s — if WebSocket dies, stale quotes expire automatically
        pipe.setex(f"quote:{symbol}", 60, payload)

    try:
        pipe.execute()
    except Exception as exc:
        logger.error("Redis write error in on_message: %s", exc)


def on_error(message):
    logger.error("Fyers WebSocket error: %s", message)


def on_close(message):
    logger.warning("Fyers WebSocket closed: %s", message)


def on_open():
    logger.info("Fyers WebSocket connection opened")



_ws_instance = None
_ws_lock = threading.Lock()


def start_websocket(
    app_id: str,
    access_token: str,
    symbols: list[str],
) -> None:
   
    global _ws_instance

    try:
        from fyers_apiv3.FyersWebsocket import data_ws  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "fyers-apiv3 is not installed. Run: pip install fyers-apiv3==3.1.3"
        )

    with _ws_lock:
        if _ws_instance is not None:
            logger.warning(
                "WebSocket already running. Stop it first before restarting."
            )
            return

        logger.info("Starting Fyers WebSocket for %d symbols", len(symbols))

        ws = data_ws.FyersDataSocket(
            access_token=f"{app_id}:{access_token}",
            log_path="",
            litemode=True,          # reduced payload — ltp + ohlc + volume
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
            reconnect=True,
            reconnect_delay=5,     
        )

        ws.subscribe(symbols=symbols, data_type="SymbolUpdate")
        _ws_instance = ws


    ws.keep_running()


def stop_websocket() -> None:
    """Stop the active WebSocket connection."""
    global _ws_instance
    with _ws_lock:
        if _ws_instance:
            try:
                _ws_instance.close_connection()
            except Exception as exc:
                logger.warning("Error closing WebSocket: %s", exc)
            _ws_instance = None
            logger.info("Fyers WebSocket stopped")


def get_live_quote(symbol: str) -> dict | None:

   
    if ":" not in symbol:
        symbol = f"NSE:{symbol}-EQ"

    try:
        r = _get_redis()
        data = r.get(f"quote:{symbol}")
        if data:
            return json.loads(data)
        return None
    except Exception as exc:
        logger.error("Redis read error in get_live_quote: %s", exc)
        return None


def get_multiple_quotes(symbols: list[str]) -> dict[str, dict | None]:
   
    normalized = {}
    for s in symbols:
        key = f"NSE:{s}-EQ" if ":" not in s else s
        normalized[s] = f"quote:{key}"

    try:
        r = _get_redis()
        pipe = r.pipeline()
        for redis_key in normalized.values():
            pipe.get(redis_key)
        values = pipe.execute()

        result = {}
        for original_symbol, raw in zip(normalized.keys(), values):
            result[original_symbol] = json.loads(raw) if raw else None
        return result

    except Exception as exc:
        logger.error("Redis pipeline error in get_multiple_quotes: %s", exc)
        return {s: None for s in symbols}
