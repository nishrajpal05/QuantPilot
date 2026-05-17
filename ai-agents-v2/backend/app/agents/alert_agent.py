
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

AlertType = Literal["email", "webhook"]
Signal = Literal["buy", "sell", "hold"]


# ─────────────────────────────────────────────────────────────────────────────
# Email via SendGrid
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(
    destination: str,
    subject: str,
    body_html: str,
) -> dict:
    """
    Send an email via SendGrid's v3 Mail Send API.

    Requires env var:  SENDGRID_API_KEY
    Requires env var:  ALERT_FROM_EMAIL  (verified sender address in SendGrid)

    Returns dict with 'success' bool and 'status_code' / 'error'.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@quantpilot.in")

    if not api_key:
        logger.error("[alert_agent] SENDGRID_API_KEY not set — cannot send email")
        return {"success": False, "error": "SENDGRID_API_KEY not configured"}

    payload = {
        "personalizations": [{"to": [{"email": destination}]}],
        "from": {"email": from_email, "name": "QuantPilot Alerts"},
        "subject": subject,
        "content": [{"type": "text/html", "value": body_html}],
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code in (200, 202):
            logger.info("[alert_agent] Email sent to %s (status %d)", destination, resp.status_code)
            return {"success": True, "status_code": resp.status_code}
        else:
            logger.error("[alert_agent] SendGrid error %d: %s", resp.status_code, resp.text[:200])
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:200]}

    except Exception as exc:
        logger.error("[alert_agent] Email send exception: %s", exc)
        return {"success": False, "error": str(exc)}


def _build_email_html(
    signal: Signal,
    symbol: str,
    price: float,
    strategy_title: str,
    algo_id: str,
    timestamp: str,
) -> tuple[str, str]:
    """Return (subject, html_body) for a signal alert email."""
    signal_colour = {"buy": "#00C87A", "sell": "#FF4D4D", "hold": "#FFA500"}.get(signal, "#888")
    signal_emoji  = {"buy": "📈", "sell": "📉", "hold": "⏸"}.get(signal, "•")

    subject = f"QuantPilot {signal_emoji} {signal.upper()} Signal — {symbol}"

    html = f"""
    <div style="font-family:Inter,sans-serif;background:#0F172A;color:#E2E8F0;
                padding:32px;max-width:480px;border-radius:12px;margin:auto;">
      <h2 style="margin:0 0 8px;font-size:22px;color:#F8FAFC;">
        QuantPilot <span style="color:{signal_colour};">{signal.upper()}</span> Signal
      </h2>
      <p style="margin:0 0 24px;color:#94A3B8;font-size:13px;">{timestamp} IST</p>

      <div style="background:#1E293B;border-radius:8px;padding:20px;margin-bottom:16px;">
        <div style="font-size:28px;font-weight:700;color:{signal_colour};">
          {signal_emoji} {signal.upper()}
        </div>
        <div style="font-size:20px;font-weight:600;margin-top:8px;">{symbol}</div>
        <div style="color:#94A3B8;font-size:14px;">₹{price:,.2f}</div>
      </div>

      <div style="background:#1E293B;border-radius:8px;padding:16px;margin-bottom:16px;">
        <div style="font-size:12px;color:#64748B;margin-bottom:4px;">STRATEGY</div>
        <div style="font-weight:600;">{strategy_title}</div>
        <div style="font-size:11px;color:#475569;margin-top:4px;font-family:monospace;">
          {algo_id}
        </div>
      </div>

      <p style="font-size:11px;color:#475569;margin:0;">
        This is an automated signal from QuantPilot. Not financial advice.
        Verify with your broker before trading.
      </p>
    </div>
    """
    return subject, html


# ─────────────────────────────────────────────────────────────────────────────
# Webhook delivery
# ─────────────────────────────────────────────────────────────────────────────

def _send_webhook(
    destination: str,
    payload: dict,
) -> dict:
    """
    POST a JSON payload to the user-supplied webhook URL.

    Timeout: 8 seconds.  No retries (caller handles scheduling).
    Supports Slack, Discord (via webhook URL), Zapier, Make, and any custom endpoint.

    Returns dict with 'success' bool and 'status_code' / 'error'.
    """
    # Slack-compatible format (also works with Discord + most generic webhooks)
    slack_payload = {
        "text": (
            f"*QuantPilot Signal* — *{payload['signal'].upper()}* {payload['symbol']} "
            f"@ ₹{payload['price']:,.2f}\n"
            f"Strategy: {payload['strategy_title']} | `{payload['algo_id']}`"
        ),
        # Standard structured payload for non-Slack endpoints
        "quantpilot": payload,
    }

    try:
        with httpx.Client(timeout=8) as client:
            resp = client.post(
                destination,
                json=slack_payload,
                headers={"Content-Type": "application/json", "User-Agent": "QuantPilot/2.0"},
            )
        if resp.status_code < 400:
            logger.info("[alert_agent] Webhook delivered to %s (status %d)", destination[:40], resp.status_code)
            return {"success": True, "status_code": resp.status_code}
        else:
            logger.error("[alert_agent] Webhook error %d: %s", resp.status_code, resp.text[:200])
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:200]}

    except Exception as exc:
        logger.error("[alert_agent] Webhook send exception: %s", exc)
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def dispatch_alert(
    alert_type: AlertType,
    destination: str,
    signal: Signal,
    symbol: str,
    price: float,
    strategy_title: str,
    algo_id: str,
) -> dict:
    """
    Dispatch a trading signal alert to the specified channel.

    Args:
        alert_type:      'email' or 'webhook'
        destination:     Email address OR webhook URL
        signal:          'buy' | 'sell' | 'hold'
        symbol:          NSE ticker (e.g. 'RELIANCE')
        price:           Current market price in INR
        strategy_title:  Human-readable strategy name
        algo_id:         SEBI algo registration ID (from compliance agent)

    Returns:
        dict with keys: success (bool), delivery (dict with channel details)
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    payload = {
        "signal": signal,
        "symbol": symbol,
        "price": price,
        "strategy_title": strategy_title,
        "algo_id": algo_id,
        "timestamp": timestamp,
    }

    logger.info(
        "[alert_agent] Dispatching %s alert → %s | signal=%s %s @ %.2f",
        alert_type, destination[:30], signal, symbol, price,
    )

    if alert_type == "email":
        subject, html = _build_email_html(signal, symbol, price, strategy_title, algo_id, timestamp)
        result = _send_email(destination, subject, html)

    elif alert_type == "webhook":
        result = _send_webhook(destination, payload)

    else:
        result = {"success": False, "error": f"Unknown alert_type: {alert_type}"}

    return {
        "success": result.get("success", False),
        "alert_type": alert_type,
        "destination": destination,
        "signal": signal,
        "symbol": symbol,
        "delivery": result,
        "dispatched_at": timestamp,
    }


def dispatch_all_alerts(
    alerts: list[dict],
    signal: Signal,
    symbol: str,
    price: float,
    strategy_title: str,
    algo_id: str,
) -> list[dict]:
    """
    Dispatch a signal to all configured alerts for a strategy.

    Args:
        alerts: List of alert dicts from DB, each with 'type' and 'destination'.
        (Other args same as dispatch_alert.)

    Returns:
        List of dispatch result dicts.
    """
    results = []
    for alert in alerts:
        if not alert.get("active", True):
            continue
        result = dispatch_alert(
            alert_type=alert["type"],
            destination=alert["destination"],
            signal=signal,
            symbol=symbol,
            price=price,
            strategy_title=strategy_title,
            algo_id=algo_id,
        )
        results.append(result)

    success_count = sum(1 for r in results if r["success"])
    logger.info(
        "[alert_agent] Dispatched %d/%d alerts for %s %s signal",
        success_count, len(results), symbol, signal,
    )
    return results
