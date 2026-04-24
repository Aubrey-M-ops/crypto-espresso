"""
Monitor — send alert messages to an admin Telegram chat on pipeline failures.

Set TELEGRAM_ADMIN_CHAT_ID in .env to your personal chat ID (get from @userinfobot).
Uses the same TELEGRAM_BOT_TOKEN as the main push channel.
If TELEGRAM_ADMIN_CHAT_ID is not set, alerts are only logged locally.

Timeout warnings: wrap pipeline steps with step_timer() to receive a Telegram
warning when a step exceeds its expected duration. Configure the default
threshold via STEP_TIMEOUT_WARN_SECONDS (default: 120).
"""

import logging
import os
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = int(os.getenv("STEP_TIMEOUT_WARN_SECONDS", "120"))


def send_timeout_warning(step: str, elapsed_sec: float, threshold_sec: int) -> None:
    """
    Send a slow-step warning to the admin Telegram chat.

    Called automatically by step_timer when elapsed > threshold.
    Never raises.
    """
    admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f"⏱ *Web3 News Push 超时警告*\n"
        f"🕐 {now}\n"
        f"📍 {step}\n"
        f"⚠️ 耗时 {elapsed_sec:.0f}s，超出预期 {threshold_sec}s"
    )

    logger.warning(f"[TIMEOUT] {step}: {elapsed_sec:.0f}s > threshold {threshold_sec}s")

    if not admin_chat_id or not bot_token:
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
            payload.pop("parse_mode")
            payload["text"] = text.replace("*", "")
            httpx.post(url, json=payload, timeout=15)
    except Exception as warn_err:
        logger.error(f"Failed to deliver timeout warning: {warn_err}")


@contextmanager
def step_timer(step: str, threshold_sec: int = _DEFAULT_TIMEOUT) -> Generator[None, None, None]:
    """
    Context manager that sends a Telegram warning if a pipeline step is too slow.

    Usage:
        with step_timer("Step 1/6: 新闻抓取", threshold_sec=60):
            articles = scrape_all_sources()
    """
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        if elapsed > threshold_sec:
            send_timeout_warning(step, elapsed, threshold_sec)


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
