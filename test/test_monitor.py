#!/usr/bin/env python3
"""
手动测试 monitor.py 是否能正常发送告警。

运行方式:
    python test/test_monitor.py

会依次检查:
  1. TELEGRAM_BOT_TOKEN 是否配置
  2. TELEGRAM_ADMIN_CHAT_ID 是否配置
  3. 发送一条真实的测试告警到你的管理员 chat
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def check_config() -> bool:
    ok = True

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

    print("🔑 检查配置...")
    if bot_token:
        print(f"  ✅ TELEGRAM_BOT_TOKEN: {bot_token[:10]}...")
    else:
        print("  ❌ TELEGRAM_BOT_TOKEN 未设置")
        print("     → 在 .env 里加: TELEGRAM_BOT_TOKEN=<从 @BotFather 获取>")
        ok = False

    if admin_chat:
        print(f"  ✅ TELEGRAM_ADMIN_CHAT_ID: {admin_chat}")
    else:
        print("  ❌ TELEGRAM_ADMIN_CHAT_ID 未设置")
        print("     → 在 .env 里加: TELEGRAM_ADMIN_CHAT_ID=<你的个人 chat ID>")
        print("     → 获取方式: 在 Telegram 搜索 @userinfobot，发送任意消息")
        ok = False

    return ok


def send_test_alert() -> bool:
    print("\n📤 发送测试告警...")
    try:
        from monitor import send_alert
        send_alert(
            step="test_monitor.py",
            error="这是一条测试告警，说明 monitor 配置正常 ✅",
        )
        print("  ✅ send_alert() 调用完成（无异常）")
        return True
    except Exception as e:
        print(f"  ❌ send_alert() 抛出异常: {e}")
        return False


def verify_delivery(admin_chat: str, bot_token: str) -> bool:
    """通过 getUpdates 无法验证主动发出的消息，改用 sendMessage 直接检查返回值。"""
    print("\n🔍 验证消息是否送达...")
    try:
        import httpx
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        resp = httpx.post(url, json={
            "chat_id": admin_chat,
            "text": "✅ [test_monitor] 验证消息：如果你看到这条，说明 Bot → Admin chat 链路正常。",
        }, timeout=15)
        data = resp.json()
        if data.get("ok"):
            print("  ✅ Telegram API 返回 ok=true，消息已送达")
            return True
        else:
            print(f"  ❌ Telegram API 返回错误: {data.get('description')}")
            return False
    except Exception as e:
        print(f"  ❌ 网络请求失败: {e}")
        return False


def main():
    print("=" * 55)
    print("Monitor 测试")
    print("=" * 55)

    if not check_config():
        print("\n⚠️  请先补全 .env 配置再重试")
        return 1

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

    if not send_test_alert():
        return 1

    if not verify_delivery(admin_chat, bot_token):
        return 1

    print("\n" + "=" * 55)
    print("✅ Monitor 可用！推送失败时你会收到 Telegram 告警。")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
