"""
Monitor — send alert messages to an admin Telegram chat on pipeline failures.

Set TELEGRAM_ADMIN_CHAT_ID in .env to your personal chat ID (get from @userinfobot).
Uses the same TELEGRAM_BOT_TOKEN as the main push channel.
If TELEGRAM_ADMIN_CHAT_ID is not set, alerts are only logged locally.
"""

import logging
import os
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


def send_alert(step: str, error: str, exc: Exception | None = None) -> None:
    """
    Send a failure alert to the admin Telegram chat.

    Never raises — alert failures are logged and swallowed so they don't
    mask the original error.

    Args:
        step:  Pipeline step label, e.g. "Step 6/6: Telegram send"
        error: Human-readable description of what went wrong
        exc:   Optional exception (its traceback tail is appended)
    """
    admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    tb_snippet = ""
    if exc:
        lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        # Keep only the last 5 lines to stay within Telegram limits
        tb_snippet = "\n```\n" + "".join(lines[-5:]).strip() + "\n```"

    text = (
        f"🚨 *Web3 News Push 报警*\n"
        f"🕐 {now}\n"
        f"📍 {step}\n"
        f"❌ {error}"
        + tb_snippet
    )

    # Always log locally
    logger.error(f"[ALERT] {step}: {error}")

    if not admin_chat_id or not bot_token:
        if not admin_chat_id:
            logger.warning(
                "TELEGRAM_ADMIN_CHAT_ID not set — alert not delivered via Telegram"
            )
        return

    try:
        import httpx

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": admin_chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        resp = httpx.post(url, json=payload, timeout=15)
        if resp.status_code != 200 or not resp.json().get("ok"):
            # Retry as plain text if Markdown parse fails
            payload.pop("parse_mode")
            payload["text"] = text.replace("```", "").replace("*", "")
            httpx.post(url, json=payload, timeout=15)
    except Exception as alert_err:
        logger.error(f"Failed to deliver Telegram alert: {alert_err}")
